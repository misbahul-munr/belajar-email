import httpx
import asyncio
import os
import random
import string
import json
from typing import *
from tqdm import tqdm

class OnesecMail:

    def __init__(self):
        self.__api_address = "https://www.1secmail.com/api/v1/"
        self.__path_json_param = os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ), 'param_request.json')
        self.__seccons = NewType("seccons", int)

    @property
    def random_username(self) -> str:
        # infinity loop if random not generate string or numbers
        while True :
            #get random string & numbers with length 10 char
            random_ = ''.join(
                random.choice(
                string.ascii_lowercase + string.digits
                ) for _ in range(10)
            ) 

            if any(x.isdigit() for x in random_ ) and any(x.isalpha() for x in random_):
                return random_

    @property
    def getsample_request(self) -> Union[dict,Exception]:
        #open json sample to return sample_parameter
        try :
            with open(self.__path_json_param,mode='r') as file :
                return json.load(file)
        except (FileNotFoundError,json.JSONDecodeError) as e :
            raise Exception(" >> json file not found ! ") from e

    async def generate_mail(self) -> Optional[str]:
        domain_req = self.getsample_request.get('domain')
        con_domain = await self.set_connection(**domain_req)
        return '{}@{}'.format(self.random_username,random.choice(con_domain)) 

    async def get_mailBox(self,address:str) -> list[dict]:
        mailbox_req = self.getsample_request.get('mailbox')
        username,domain = address.split('@')
        mailbox_req.update({'login':username,'domain':domain})
        con_mailbox = await self.set_connection(**mailbox_req)
        return con_mailbox

    async def get_latest_message(self,address:str,get_desc=False) -> Union[None,dict,str]:
        mssg_req =  self.getsample_request.get('messages')
        mailbox = await self.get_mailBox(address)
        try:
            id_ = mailbox[0].get('id')
        except IndexError:
            return None
        username,domain = address.split('@')
        mssg_req.update({'login':username,'domain':domain,'id':id_})
        con_latest_message = await self.set_connection(**mssg_req)
        output = con_latest_message.get('textBody')
        if not get_desc :
            return None if output is None else output.strip() if output.strip() else '-'
        else :
            return {key:item for key,item in con_latest_message.items()}
    
    async def wait_newMessage(self,address:str,time_out:int=60,filters:str=None):
        """
            Waits for a new message within a specified timeout period.

            Parameters:
            address (str): The email address to check for messages.
            time_out (int): The timeout value in seconds (seccons). Default is 60 seconds.
            filters (str, optional): A filter string to match specific messages.

            Returns:
            None
        """

        all_inbox = await self.get_mailBox(address)
        old_all_id = list(map(lambda x:x['id'],all_inbox))
        secconds = 0

        async def update_message() :
            await asyncio.sleep(3)
            return list(filter(lambda x:x['id'] not in old_all_id, await self.get_mailBox(address)))

        with tqdm(total=time_out,desc="waiting new message",unit='sec',colour='green') as pbar :
            while time_out > secconds :
                try:
                    if await update_message():
                        if filters is None:
                            pbar.close()
                            return await self.get_latest_message(address)
                        else :
                            dict_message = await self.get_latest_message(address,True)
                            if any(filters.lower() in str(value).lower() for value in dict_message.values()):
                                pbar.close()
                                return await self.get_latest_message(address)

                except httpx.HTTPStatusError :
                    pass

                secconds += 4
                pbar.update(4)
                await asyncio.sleep(1)

            pbar.close()

    async def set_connection(self,downloads=False,**kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(self.__api_address,params=kwargs) 
            r.raise_for_status() # bad requests if status code not 2xx
            return r.json() 

