import aiohttp

from data.settings import SMS_ACTIVATOR_API_KEY


class SMSActiwatorAPI(object):
    def __init__(self, session: aiohttp.ClientSession):
        self.api_key: str = SMS_ACTIVATOR_API_KEY
        self.session = session
        self.url: str = "https://sms-acktiwator.ru/api/"
        self.id = 534
        self.code = 'RU'

    async def get_balance(self) -> float:
        async with self.session.get(url=f"{self.url}getbalance/{self.api_key}") as balance:
            return float(await balance.text())

    async def get_number(self) -> dict:
        async with self.session.get(url=f"{self.url}getnumber/{self.api_key}?id={self.id}&code={self.code}") as number:
            return await number.json()

    async def get_active_activation(self, id: str) -> str:
        async with self.session.get(url=f"{self.url}getlatestcode/{self.api_key}?id={id}") as number:
            return await number.text()

    async def change_number_status(self, id: str, status: str) -> str:
        async with self.session.get(url=f"{self.url}setstatus/{self.api_key}?id={id}&status={status}") as number:
            return await number.text()
