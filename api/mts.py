import random
import string
import aiohttp


class MtsAPI(object):
    def __init__(self, phone_number: str, session: aiohttp.ClientSession, allowed_tariff_list: list = None):
        if allowed_tariff_list is None:
            allowed_tariff_list = ['9a1ca77a-bec5-4df5-a0a2-dedc974143e1', 'e696f175-7bc4-4f0c-b229-548ee6b6bed4',
                                   'c3be0b5c-760e-43e5-b089-24336ced1950']
        self.phone_number = phone_number
        self._session = session
        self.allowed_tariff_list = allowed_tariff_list

    async def get_mts_premium(self) -> bool:
        tariff_list = await self.__get_tariff_list()
        contains_tariff = [tariff_data['contentId'] for tariff_data in tariff_list if
                           tariff_data['contentId'] in self.allowed_tariff_list]
        if not contains_tariff:
            return False
        activate_mts_data = await self.__activate_mts_premium(random.choice(contains_tariff))
        if activate_mts_data:
            return True
        return False

    async def __get_tariff_list(self) -> list[dict]:
        async with self._session.get(
                f'https://api.music.yandex.net/payclick/content-provider/available-subscriptions?msisdn={self.phone_number}') as response:
            tariff_list = await response.json()
            return tariff_list

    async def __activate_mts_premium(self, tariff: str) -> dict:
        access_headers_yandex = {
            "Authorization": "OAuth y0_AgAAAABsmBQLAAKkvAAAAADkYx2aUFS5mnJkTP-InW6Z-ecJJM0iMLI",
            "Content-Type": "application/json"
        }
        uid = await self.__generate_uid()
        bid = await self.__generate_bid()
        json_data = {
            "userId": f"00000000100090099{uid}",
            "bindingId": f"88b32A591b86Dbcaa98b{bid}",
            "msisdn": self.phone_number.replace("+", "", 1),
            "contentId": tariff
        }
        async with self._session.post(url='https://api.music.yandex.net/payclick/subscriptions',
                                      headers=access_headers_yandex, json=json_data) as response:
            mts_premium_status = await response.json(content_type=None)
            return mts_premium_status

    @staticmethod
    async def __generate_uid():
        return ''.join(random.choice(string.digits) for _ in range(3))

    @staticmethod
    async def __generate_bid():
        return ''.join(random.choice(string.hexdigits + string.digits) for _ in range(12))
