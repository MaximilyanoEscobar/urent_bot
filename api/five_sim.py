import aiohttp

from data.settings import FIVE_SIM_API_KEY


class FiveSIM:
    def __init__(self, session: aiohttp.ClientSession, phone_number=None, id_number=None):
        self.api_key = FIVE_SIM_API_KEY
        self.phone_number = phone_number
        self.id_number = id_number
        self.session = session
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

    async def get_balance(self) -> float:
        async with self.session.get('https://5sim.biz/v1/user/profile', headers=self.headers) as response:
            response_json = await response.json()
            return response_json['balance']

    async def cancel_number(self) -> bool:
        async with self.session.get(f'https://5sim.biz/v1/user/cancel/{self.id_number}',
                                    headers=self.headers) as response:
            if response.status == 200:
                return True
            return False

    async def ban_number(self) -> bool:
        async with self.session.get(f'https://5sim.biz/v1/user/ban/{self.id_number}',
                                    headers=self.headers) as response:
            if response.status == 200:
                return True
            return False

    async def finish_number(self) -> bool:
        async with self.session.get(f'https://5sim.biz/v1/user/finish/{self.id_number}',
                                    headers=self.headers) as response:
            if response.status == 200:
                return True
            return False

    async def check_number(self) -> dict | None:
        async with self.session.get(f'https://5sim.biz/v1/user/check/{self.id_number}',
                                    headers=self.headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
