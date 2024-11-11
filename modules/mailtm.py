import httpx
import random 
import string 
import asyncio
import os 
import re
import json
from typing import *
from tqdm import tqdm

class Crud:

    __path_log = os.path.join(
        os.path.dirname(
            os.path.realpath(__file__).replace("modules", 'log')
        ),'mailtm_created'
    )
    os.makedirs(__path_log,exist_ok=True)

    def convrt_filename(self,namefile) -> str :
        """ add file name to path log """

        if '.json' in namefile.lower():
            return os.path.join(self.__path_log,namefile)
        else :
            return os.path.join(self.__path_log,f'{namefile}.json')

    def view_config(self,json_file:str) -> dict:
        try:
            with open(self.convrt_filename(json_file),mode='r') as file:
                return json.load(file)

        except (FileNotFoundError,json.JSONDecodeError):
            return {}

    def get_value_item(self,patern_value) -> Optional[dict]:
        all_account = self.list_account
        for x in all_account :
            my_dict = self.view_config(x)
            if patern_value.lower() in [str(x).lower() for x in my_dict.values()]:
                return my_dict

    def make_config(self,file_name,kwargs:dict):
        my_dict = self.view_config(file_name)
        my_dict.update({**kwargs})
        with open(self.convrt_filename(file_name),mode='w') as file :
            json.dump(my_dict, file, indent=4)

    @property
    def list_account(self) -> list :
        try:
            return os.listdir(self.__path_log)
        except OSError:
            return []

    def delete_config(self,json_file) -> bool :
        try:
            os.remove(self.convrt_filename(json_file))
            return True
        except FileNotFoundError:
            return False

class Mailtm :
    def __init__(self):
        self.__api_address = "https://api.mail.tm"
        self.__crud = Crud()

    @property 
    def random_username(self) -> str:
        strings = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        numbers = ''.join(random.choice(string.digits) for _ in range(5))
        gather = list(map(lambda x:f'{x[1]}{numbers[x[0]]}', enumerate(strings)))
        return ''.join(gather)

    async def set_connection(self,method:str,endpoint:str ,header:dict | None = None, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient() as client :
            if method in ['get','post','delete']:
                response = await getattr(client, method)(f'{self.__api_address}/{endpoint}',headers = header,**kwargs)
            else :
                raise Exception(" >> method not valid ! ")

            return response

    async def getRanDomdomain(self) -> str | None:
        response = await self.set_connection("get",'domains',header={'Accept':'Application/ld+json'},params={'page':1})
        if response.status_code == 200 :
            data = response.json()
            return random.choice(list(map(lambda x:x.get('domain'),data.get('hydra:member'))))

    async def generate_token(self,address,password) -> dict | httpx.Response:
        response = await self.set_connection('post', 'token',header={
            "Accept":'application/json'
        },json = {'address':address,'password':password})
        if response.status_code == 200 :
            return response.json()
        return response

    async def generate(self,customUsername:str=None) -> dict | httpx.Response:
        """ generate random Email """
        if customUsername is None :
            customUsername = self.random_username

        address = "{}@{}".format(customUsername,await self.getRanDomdomain())
        password = self.random_username
        response = await self.set_connection('post', 'accounts',header={
            'Accept':'application/ld+json',
            'Content-Type':'application/json'
        },json={ 'address':address,'password':password })

        if response.status_code in [200,201]:
            data = response.json()
            my_dict = {k:v for k,v in data.items()}
            my_dict.update({'password':password,'address':address})
            gen_token = await self.generate_token(address, password)
            if gen_token is not None:
                my_dict.update(token=gen_token.get('token'))
                self.__crud.make_config(data.get('id'),my_dict)
                return address
            else:
                return gen_token.status_code
        else :
            return response.status_code

    async def get_inbox(self,address:str) -> Union[list[dict],Exception,httpx.Response]:
        """ get all message for your address """
        try:
            my_token = self.__crud.get_value_item(address).get('token')
        except AttributeError:
            raise Exception(f" >> {address} do not have token ! ")

        response = await self.set_connection("get", 'messages',header={
            "Accept" : 'application/ld+json',
            "Authorization": f"Bearer {my_token}"
        },params= {'page':1})
        if response.status_code == 200 :
            return response.json().get('hydra:member')
        return response

    async def get_latest_message(self,address:str,all_desc:bool=False) -> str | Exception | None:
        list_inbox = await self.get_inbox(address)
        token = self.__crud.get_value_item(address).get("token")
        if len(list_inbox) >= 1 :
            mssg_id = list_inbox[0].get("id")
            response = await self.set_connection("get", f'messages/{mssg_id}',header= {
                'Accept': 'application/ld+json',
                'Authorization':f'Bearer {token}'
            })
            if response.status_code == 200 :
                if all_desc:
                    return response.json()
                else:
                    output = response.json().get('text')
                    return output.strip() if output.strip() else output
            else :
                raise Exception(response.status_code)
        else :
            return None

    async def wait_new_message(self,address:str,filters:str|None = None,time_out:int=60) -> Optional[str]:
        """ 
        Waiting for the latest message, with or without filtering the text message  

        Parameters :
        address (str): username@domain for your mail
        filters (str): filters any pattern text message
        time_out (int): seconds time wait for message default is 60 sec

        Returns:
        None
        """
        old_id_inbox = list(map(lambda x : x['id'] ,await self.get_inbox(address)))
        seconds = 0

        async def new_id_inbox():
            await asyncio.sleep(3)
            return list(filter(lambda x:x['id'] not in old_id_inbox , await self.get_inbox(address)))

        def check_pattern_in_values(data:Iterable, pattern:str) -> bool :
            if isinstance(data, dict):
                for value in data.values():
                    if check_pattern_in_values(value, pattern):
                        return True
            elif isinstance(data, list):
                for item in data:
                    if check_pattern_in_values(item, pattern):
                        return True
            elif isinstance(data, str):
                if re.search(pattern, data, re.IGNORECASE):
                    return True
            return False

        with tqdm(desc="Waiting new Message ",total=time_out,colour='red',unit='sec') as pbar:
            while seconds <= time_out :
                try:
                    if await new_id_inbox() :
                        if filters is None :
                            pbar.close()
                            return await self.get_latest_message(address)
                        else :
                            data_latest = await self.get_latest_message(address,True)
                            if check_pattern_in_values(data_latest, filters):
                                pbar.close()
                                out = data_latest.get('text')
                                return out.strip() if out.strip() else out
 
                except httpx.HTTPStatusError:
                    pass

                await asyncio.sleep(1)
                seconds+=4
                pbar.update(4)

            pbar.close()
            return None

    async def delete_account(self,address:str) -> bool:
        my_dict= self.__crud.get_value_item(address)
        response = await self.set_connection("delete", 'accounts/{}'.format(my_dict.get('id')),header={
            "Accept":'*/*',
            "Authorization": 'Bearer {}'.format(my_dict.get("token"))
        })

        if response.status_code == 204 :
            return True if self.__crud.delete_config(my_dict.get('id')) else False
        else :
            return False
