import traceback
from functools import wraps

import aiohttp


class Zeon:
    def __init__(self, port, session: aiohttp.ClientSession):
        self.url = f'https://zeon-shop.online:{port}'
        self.session = session

    @staticmethod
    def __print_response(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            print(f"========================= {func.__name__} ============================")
            try:
                print(performed_func := await func(self, *args, **kwargs))
                return performed_func
            except Exception:
                print(traceback.format_exc())
            finally:
                print(f"========================= {func.__name__} ============================")

        return wrapper

    @__print_response
    async def payment_create(self, acs_url, pa_req, md, bot_username):
        data = {
            "payment_url": f"{acs_url}",
            "pa_req": f"{pa_req}",
            "md": f"{md}",
            "bot_username": f"{bot_username}"}
        async with self.session.post(url=f'{self.url}/urent/payment/create/', json=data) as response_create:
            return await response_create.json()

    @__print_response
    async def payment_check(self, url_id):
        async with self.session.get(url=f'{self.url}/urent/check/payment/?url={url_id}') as response_payment:
            return await response_payment.json()
