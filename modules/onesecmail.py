import httpx
import asyncio
import os
import random
import string
import json
from typing import *


class OnesecMail:

    def __init__(self):
        self.__api_address = "https://www.1secmail.com/api/v1/"
        self.__path_json_param = os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ), 'param_request.json')

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
        except (FileNotFoundError,json.JSONDecodeError):
            raise Exception(" >> json file not found ! ")

    # send to api action value parameter
    async def set_connection(self,actions,**kwargs) -> Optional[Dict]:
        #add action parameter to kwargs
        kwargs.update(action = actions)
        #async request with httpx
        async with httpx.AsyncClient() as client:
            # request api onesecmail
            r = await client.get(self.__api_address,params=kwargs) 
            if r.status_code == 200 :
                return await r.json()
            else :
                print(r.status_code)
                return None


if __name__ == "__main__":
    app = OnesecMail()


