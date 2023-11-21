import aiohttp


class Nominatim:
    def __init__(self, user_agent: str):
        self.headers = {
            'User-Agent': user_agent,
            'Content-Type': 'application/json; charset=UTF-8'
        }

    async def get_address(self, lat: int | str, lng: int | str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}', headers=self.headers) as response:
                response_json = await response.json()
                try:
                    return response_json['address']['city']
                except Exception:
                    return "undefined"
