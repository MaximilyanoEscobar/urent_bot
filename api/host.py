import aiohttp


class Host:
    def __init__(self, port_server: int, session: aiohttp.ClientSession):
        self.url = f'http://82.147.84.225:{port_server}'
        self.session = session

    async def upload_account(self, phone_number, access_token, refresh_token, count_bonus):
        data = {
              "number": f"{phone_number}",
              "access_token": access_token,
              "refresh_token": refresh_token,
              "optional_field": {},
              "points": count_bonus
            }
        async with self.session.post(f'{self.url}/urent/upload/account/', json=data) as response_account:
            return await response_account.json()

