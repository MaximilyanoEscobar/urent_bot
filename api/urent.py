import random
import traceback
from functools import wraps
from pprint import pprint
from urllib.parse import parse_qs

import aiohttp
from aiogram import Bot
from aiogram.fsm.context import FSMContext

from data.settings import PROXY
from db.repository import account_repository


class UrentAPI(object):

    def __init__(self,
                 session: aiohttp.ClientSession,
                 refresh_token=None,
                 phone_number=None,
                 access_token=None,
                 coupon=None
                 ):
        super(UrentAPI, self).__init__()
        self.refresh_token: str = refresh_token
        self.phone_number: int | str | None = phone_number
        self.coupon: str | None = coupon
        self.session = session
        self.access_token: str = access_token
        self.headers = {
            'authorization': f'Bearer {self.access_token}'
        }

    # ==================================================
    # DECORATOR
    # ==================================================

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

    # ==================================================
    # DECORATOR
    # ==================================================

    @__print_response
    async def binding_credit_card(self, card_number: str, expiry_year: str, expiry_month: str, csc: str, bot: Bot,
                                  payment_method: str, state: FSMContext) -> dict[str: str | None, str: None | str]:
        if payment_method == 'yoo':
            tokens = await self._yookassa_tokens(card_number=card_number, expiry_year=expiry_year,
                                                 expiry_month=expiry_month, csc=csc, bot=bot)

            if tokens is None:
                return {'error': 'Error in self._tokens method', 'confirmation_url': None}

            if tokens.get('type') is not None:
                error = tokens['description']
                return {'error': error, 'confirmation_url': None}

            payment_token: str = tokens['payment_token']
            payment_data = await self._yookassa_add_card(payment_token=payment_token)
            confirmation_url: str = payment_data.get('confirmationUrl')

            if confirmation_url is None:
                error = payment_data['errors'][0]['value'][0]
                return {'error': error, 'confirmation_url': None}

            dict_from_confirmation_url = parse_qs(confirmation_url)

            try:
                orderN: str = dict_from_confirmation_url['orderN'][0]
                fingerprint_check_data = await self._yookassa_fingerprint_check(orderN=orderN)
                if fingerprint_check_data.get('challenge') is not None:
                    return {'error': None, 'confirmation_url': confirmation_url}

            except KeyError:
                return {'error': None, 'confirmation_url': confirmation_url}

            return {'error': None, 'confirmation_url': None}

        elif payment_method == 'cloud':
            ...

    @__print_response
    async def _yookassa_tokens(self, card_number, expiry_year, expiry_month, csc, bot) -> dict:
        bot_info = await bot.get_me()
        return_url = f'https://t.me/{bot_info.username}'
        headers = {
            "Authorization": "Basic bGl2ZV9PVEU1TmpJekNPMFRLcnRVdXRXMXRkaUU4azlxTUNUNmNzeDFTcWFuUlhFOg==",
            "Content-Type": "application/json",
            "User-Agent": "YooKassa.SDK.Client.Android/6.5.3 Android/7.1.2 smartphone",
            "Host": "sdk.yookassa.ru"
        }
        payload = {"tmx_session_id": "Configuration Error", "amount": {"value": "15.00", "currency": "RUB"},
                   "save_payment_method": True, "payment_method_data": {"type": "bank_card",
                                                                        "card": {"number": card_number,
                                                                                 "expiry_year": expiry_year,
                                                                                 "expiry_month": expiry_month,
                                                                                 "csc": csc}},
                   "confirmation": {"type": "redirect", "return_url": return_url}}
        async with self.session.post(url='https://sdk.yookassa.ru/api/frontend/v3/tokens', json=payload,
                                     headers=headers, proxy=PROXY) as response:
            return await response.json()

    @__print_response
    async def _yookassa_add_card(self, payment_token) -> dict:
        payload = {"token": payment_token}
        async with self.session.post(url='https://service.urentbike.ru/gatewayclient/api/v1/yookassa/addcard',
                                     json=payload, headers=self.headers, proxy=PROXY) as response:
            return await response.json()

    @__print_response
    async def _yookassa_fingerprint_check(self, orderN):
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; ASUS_Z01QD Build/N2G48H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 ",
            "Accept": "*/*"
        }
        payload = {"orderN": orderN}
        while True:
            async with self.session.post(url="https://paymentcard.yoomoney.ru/3ds/fingerprint/check", headers=headers,
                                         json=payload) as response:
                response_json = await response.json()
                status = response_json['status']
                if status == 'success':
                    return response_json['result']

    # ==================================================
    # MAIN REQUESTS
    # ==================================================

    @__print_response
    async def payment_acquiring_setting(self, status_code=401):
        while status_code == 401:
            async with self.session.get(
                    'https://service.urentbike.ru/gatewayclient/api/v1/payment/acquiring_settings?countryCode=rus&cityName=&priorityAcquiring=Cloudpayments',
                    headers=self.headers, proxy=PROXY) as response_payment:
                status_code = response_payment.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                return await response_payment.json()

    @__print_response
    async def ash_magnzona_urent_cloud_crypto(self, card_number, card_date, card_cvc, cloud_payments_public_id):
        data = {
            "card_number": card_number,
            "date": f"{card_date}",
            "csc": f"{card_cvc}",
            "public_id": f"{cloud_payments_public_id}"
        }
        async with self.session.post('https://ash.magnzona.ru/urent/cloud_crypto', json=data) as response_cloud_crypto:
            return await response_cloud_crypto.json()

    @__print_response
    async def cloudpayments_card(self, cryptogram):
        data = {"cardCryptogramPacket": f"{cryptogram}",
                "cardHolder": ""
                }
        async with self.session.post('https://service.urentbike.ru/gatewayclient/api/v1/cloudpayments/card',
                                     headers=self.headers, json=data, proxy=PROXY) as response_card:
            return await response_card.json()

    @__print_response
    async def acs_url(self, acs_url, pa_req, md):
        headers = {
            'Host': 'api.cloudpayments.ru',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; ASUS_I003DD Build/N2G48H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/68.0.3440.70 Mobile Safari/537.36',
            'Origin': 'https://api.cloudpayments.ru',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'ru-RU,en-US;q=0.9',
            'X-Requested-With': 'ru.urentbike.app'
        }
        data = f'PaReq={pa_req}&MD={md}&TermUrl=https%3A%2F%2Fdemo.cloudpayments.ru%2FWebFormPost%2FGetWebViewData'
        async with self.session.post(url=acs_url, headers=headers, data=data) as response_acs_url:
            return await response_acs_url.json()

    @__print_response
    async def cloudpayments_post3ds(self, md, pa_res):
        data = {"md": md,
                "paRes": pa_res
                }
        async with self.session.post('https://service.urentbike.ru/gatewayclient/api/v1/cloudpayments/post3ds',
                                     json=data, headers=self.headers) as response_post3ds:
            return await response_post3ds.json()

    @__print_response
    async def activate_promo_code(self, promo_code: str, status_code=401) -> dict | bool:
        while status_code == 401:
            payload = {"promoCode": promo_code}
            async with self.session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/profile/promocode",
                                         headers=self.headers, json=payload, proxy=PROXY) as response_promo_code:
                status_code = response_promo_code.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                return await response_promo_code.json()

    @__print_response
    async def get_plus_info(self, status_code=401) -> dict | bool:
        while status_code == 401:
            async with self.session.get(url=f"https://service.urentbike.ru/gatewayclient/api/v1/subscriptions/my",
                                        headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    response_json: dict = await response.json()
                    return response_json

    async def get_credit_card_details(self, status_code=401) -> dict | bool:
        while status_code == 401:
            async with self.session.get(url="https://service.urentbike.ru/gatewayclient/api/v1/payment/profile",
                                        headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    async def remove_card(self, card_id: int, status_code=401) -> dict | bool:
        while status_code == 401:
            async with self.session.delete(
                    url=f"https://service.urentbike.ru/gatewayclient/api/v1/cards/cards/{card_id}",
                    headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    async def get_active_travel(self, status_code=401) -> dict | bool:
        while status_code == 401:
            async with self.session.get(url="https://service.urentbike.ru/gatewayclient/api/v2/activity",
                                        headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    await self.refresh_access_and_refresh_token()
                else:
                    return await response.json()

    async def remove_pause_drive(self, scooter_id, lat, lng, status_code=401) -> dict | bool:
        while status_code == 401:
            payload = {
                "locationLat": lat,
                "locationLng": lng,
                "isQrCode": False,
                "rateId": "",
                "Identifier": scooter_id,
                "withInsurance": False
            }
            async with self.session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/order/resume",
                                         headers=self.headers, json=payload, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    async def pause_drive(self, scooter_id, lat, lng, status_code=401) -> dict | bool:
        while status_code == 401:
            data = {
                "locationLat": lat,
                "locationLng": lng,
                "isQrCode": False,
                "rateId": "",
                "Identifier": scooter_id,
                "withInsurance": False
            }
            async with self.session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/order/wait",
                                         headers=self.headers, json=data, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    async def stop_drive(self, scooter_id, status_code=401) -> dict | bool:
        while status_code == 401:
            url = "https://service.urentbike.ru/gatewayclient/api/v1/order/end"
            locations = random.choice([{"lat": 44.99708938598633, "lng": 39.07448959350586},
                                       {"lat": 45.01229183333333, "lng": 39.07393233333333},
                                       {"lat": 44.55036283333334, "lng": 38.0856945},
                                       {"lat": 44.5753125, "lng": 38.066902166666665},
                                       {"lat": 44.87790683333333, "lng": 37.33355566666667},
                                       {"lat": 44.90170366666666, "lng": 37.3204025},
                                       {"lat": 43.41010516666667, "lng": 39.936585666666666},
                                       {"lat": 43.387023500000005, "lng": 39.99113166666667},
                                       {"lat": 43.90788650512695, "lng": 39.3329963684082},
                                       {"lat": 43.920260999999996, "lng": 39.31842066666666},
                                       ])
            payload = {
                "locationLat": locations["lat"],
                "locationLng": locations["lng"],
                "Identifier": scooter_id,

            }
            async with self.session.post(url=url, headers=self.headers, json=payload, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    @__print_response
    async def start_drive(self, lat, lng, id_tariff, scooter_id, status_code=401) -> dict | bool:
        while status_code == 401:
            json_data = {"locationLat": lat,
                         "locationLng": lng,
                         "isQrCode": False,
                         "rateId": id_tariff,
                         "Identifier": f"S.{scooter_id}",
                         "withInsurance": False
                         }
            async with self.session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/order/make",
                                         headers=self.headers, json=json_data, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    @__print_response
    async def refresh_access_and_refresh_token(self) -> bool:
        """
        Получение нового access_token'a и проверка на бан аккаунта | умирание refresh_token'a
        :return: is_banned: bool | response_json: dict
        """
        url = "https://service.urentbike.ru/gatewayclient/api/v1/connect/token"
        payload = {
            "client_id": "mobile.client.android",
            "client_secret": "95YvCeLj74Zma3SPqyH8SwgzYMtMBj5C8FxPu5xHVExwJBjMn2t7S9L4HADQaAkc",
            "grant_type": "refresh_token",
            "scope": "bike.api ordering.api location.api customers.api payment.api maintenance.api notification.api "
                     "log.api ordering.scooter.api driver.bike.lock.offo.api driver.scooter.ninebot.api identity.api "
                     "offline_access",
            "refresh_token": self.refresh_token
        }
        rewrite_headers = self.headers.copy()
        del rewrite_headers['authorization']
        pprint(rewrite_headers)
        async with self.session.post(url=url, headers=rewrite_headers, data=payload, proxy=PROXY) as response:
            response_json = await response.json()
            refresh_token = response_json.get('refresh_token')
            access_token = response_json.get('access_token')
            if refresh_token is not None and access_token is not None:
                self.access_token = access_token
                self.headers = {**self.headers, **{"authorization": f'Bearer {self.access_token}'}}
                while True:
                    try:
                        await account_repository.update_access_refresh_token_by_number(number=self.phone_number,
                                                                                       access_token=access_token,
                                                                                       refresh_token=refresh_token)
                        return False
                    except Exception as ex:
                        print(f'Error: {ex}')
            else:
                while True:
                    try:
                        await account_repository.update_account_status_by_number(number=self.phone_number)
                        return True
                    except Exception as ex:
                        print(f'Error: {ex}')

    @__print_response
    async def get_profile(self, status_code=401) -> dict | bool:
        """
        :param status_code: 401 - получение нового access_token'а
        :return: True - если выдали бан, dict - если запрос прошёл
        """
        while status_code == 401:
            url = "https://service.urentbike.ru/gatewayclient/api/v1/payment/profile"
            async with self.session.get(url=url, headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    @__print_response
    async def check_card_availability(self, status_code=401):
        while status_code == 401:
            async with self.session.get(url="https://service.urentbike.ru/gatewayclient/api/v1/cards",
                                        headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    if await self.refresh_access_and_refresh_token():
                        return True
                else:
                    return await response.json()

    @__print_response
    async def get_scooter_info(self, scooter_id: str | int, status_code=401) -> dict:
        while status_code == 401:
            async with self.session.get(
                    url=f"https://service.urentbike.ru/gatewayclient/api/v3/transports/S.{scooter_id}",
                    headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    await self.refresh_access_and_refresh_token()
                else:
                    return await response.json()

    @__print_response
    async def get_cloud_payments_public_id(self, status_code=401) -> str:
        while status_code == 401:
            url = 'https://service.urentbike.ru/gatewayclient/api/v1/payment/acquiring_settings?countryCode=rus&cityName=&priorityAcquiring=Cloudpayments'
            async with self.session.get(url=url, headers=self.headers, proxy=PROXY) as response:
                status_code = response.status
                if status_code == 401:
                    await self.refresh_access_and_refresh_token()
                else:
                    response_json = await response.json()
                    return response_json['settings']['publicId']

    @__print_response
    async def get_user_id(self, status_code=401):
        while status_code == 401:
            rewrite_headers = self.headers.copy()
            rewrite_headers.pop('ur-user-id')
            async with self.session.get(url="https://service.urentbike.ru/gatewayclient/api/v1/profile",
                                        headers=rewrite_headers, proxy=PROXY) as response_profile:
                status_code = response_profile.status
                if status_code == 401:
                    await self.refresh_access_and_refresh_token()
                else:
                    pprint(response_profile := await response_profile.json())
                    self.user_id = response_profile['id']
                    self.headers = {**self.headers, **{"ur-user-id": self.user_id}}

    """Ебучий случай вход на личный аккаунт"""

    @__print_response
    async def ash_magnzona_urent_verify_phone(self) -> dict:
        async with self.session.get(
                url=f'https://ash.magnzona.ru/urent/verify/{self.phone_number}/') as response_verify:
            return await response_verify.json()

    @__print_response
    async def ash_magnzona_urent_attempt(self, sms_code, session_id) -> dict:
        async with self.session.get(
                url=f'https://ash.magnzona.ru/urent/attempt/{self.phone_number}/{sms_code}/{session_id}') as response_attempt:
            return await response_attempt.json()

    @__print_response
    async def full_url(self, full_url: str) -> dict:
        async with self.session.get(url=full_url, proxy=PROXY) as response_full_url:
            return await response_full_url.json()

    @__print_response
    async def mobile_social(self, attempt_token, system_id, social_id):
        data = {
            "phoneNumber": self.phone_number,
            "phoneModel": "Unknown",
            "socialAccountAccessToken": attempt_token,
            "uniqueid": system_id,
            "socialType": "NotifyMailRu",
            "locationLng": "45.055510",
            "socialAccountId": social_id,
            "locationLat": "39.031073",
            "osVersion": "15.1.0"
        }
        async with self.session.post(url='https://service.urentbike.ru/gatewayclient/api/v1/mobile/social',
                                     proxy=PROXY,
                                     json=data) as response_social:
            return await response_social.json()

    @__print_response
    async def connect_token(self, device_id, session_id, system_id, sms_auto_code):
        headers = {
            'ur-device-id': device_id,
            'ur-platform': 'Android',
            'ur-_session': session_id,
            'ur-user-id': system_id,
            'ur-version': '1.13',
            'user-agent': 'Urent/1.13 (ru.urentbike.app; build: 1120; Android 7.1.4 okhttp/4.9.1',
            'accept-language': 'ru-RU',
            'accept-encoding': 'gzip',
            'content-type': 'application/x-www-form-urlencoded'
        }
        data = f'client_id=mobile.client.android&client_secret=95YvCeLj74Zma3SPqyH8SwgzYMtMBj5C8FxPu5xHVExwJBjMn2t7S9L4HADQaAkc&grant_type=password&locationLat=50.78346689795775&locationLng=60.54086571564948&password={sms_auto_code}&scope=bike.api ordering.api location.api customers.api payment.api offline_access maintenance.api notification.api log.api ordering.scooter.api driver.bike.lock.tomsk.api driver.bike.lock.offo.api driver.scooter.ninebot.api identity.api&username={self.phone_number}'
        async with self.session.post(url='https://service.urentbike.ru/gatewayclient/api/v1/connect/token',
                                     proxy=PROXY,
                                     data=data,
                                     headers=headers) as response_token:
            return await response_token.json()

    # # REGISTRATION SYKA BLYAT NAXYU
    #
    # async def registration_account(self):
    #     system_id: str = str(uuid.uuid4()).upper()
    #     # phone_number: str = f'+{self.phone_number}'
    #     phone_number: str = '79199083874'
    #     device_id: str = str(uuid.uuid4()).upper()
    #     session_id: str = uuid.uuid4().hex
    #     application_id: str = str(uuid.uuid4())
    #     push_token: str = uuid.uuid4().hex + uuid.uuid4().hex
    #
    #     _send_mobile_code_json = await self._send_mobile_code(application_id=application_id,
    #                                                           device_id=device_id,
    #                                                           phone_number=phone_number,
    #                                                           push_token=push_token,
    #                                                           session_id=session_id,
    #                                                           system_id=system_id)
    #
    #     sms_code = input('SMS CODE: ')
    #     _send_sms_code_json = await self._send_sms_code_to_verify(sms_code=sms_code, session_id=session_id,
    #                                                               application_id=application_id)
    #     token = _send_mobile_code_json['token']
    #
    # @__print_response
    # async def _send_mobile_code(self, application_id, device_id, phone_number, push_token, session_id,
    #                             system_id) -> dict:
    #     apiRequestParams = {
    #         'application_id': application_id,
    #         'application': 'urent',
    #         'capabilities': 'call_number_fragment,ping_v2',
    #         'checks': 'push,sms',
    #         'device_id': device_id,
    #         'device_name': 'Unknown',
    #         'language': 'RU',
    #         'libverify_build': '111',
    #         'libverify_version': '1.10.0',
    #         'os_version': '15.0',
    #         'phone': phone_number,
    #         'platform': 'ios',
    #         'push_token': push_token,
    #         'service': 'urent_registration',
    #         'session_id': session_id,
    #         'system_id': system_id,
    #         'version': '1'}
    #     pprint(apiRequestParams)
    #     treeSet = set()
    #     for key, value in apiRequestParams.items():
    #         encoded_value = urllib.parse.quote_plus(str(value))
    #         treeSet.add(key + encoded_value)
    #     treeSet = sorted(treeSet)
    #     method_name = 'verify'
    #     application_key_hex = '3352634c48474f7566765044735434484768377271725a5852394a566733584b'
    #     finally_string = method_name + ''.join(treeSet) + application_key_hex
    #     signature = urllib.parse.quote(hashlib.md5(finally_string.encode('utf-8')).hexdigest())
    #     params = apiRequestParams
    #     params['signature'] = signature
    #
    #     async with self._session.get(url='https://clientapi.mail.ru/fcgi-bin/verify?', params=params,
    #                                 proxy='http://192.168.27.13:8888') as response:
    #         return await response.json()
    #
    # @__print_response
    # async def _send_sms_code_to_verify(self, sms_code: str, session_id: str, application_id: str):
    #     apiRequestParams = {
    #         'application_id': application_id,
    #         'application': 'urent',
    #         'code': sms_code,
    #         'code_source': 'USER_INPUT',
    #         'id': session_id,
    #         'internal': 'verify',
    #         'language': 'ru_RU',
    #         'phone': self.phone_number,
    #         'platform': 'android',
    #         'service': 'urent_registration'
    #     }
    #     treeSet = set()
    #     for key, value in apiRequestParams.items():
    #         encoded_value = urllib.parse.quote_plus(str(value))
    #         treeSet.add(key + encoded_value)
    #     treeSet = sorted(treeSet)
    #     method_name = 'attempt'
    #     application_key_hex = '3352634c48474f7566765044735434484768377271725a5852394a566733584b'
    #     finally_string = method_name + ''.join(treeSet) + application_key_hex
    #     signature = urllib.parse.quote(hashlib.md5(finally_string.encode('utf-8')).hexdigest())
    #     params = apiRequestParams
    #     params['signature'] = signature
    #     async with self._session.get(url='https://clientapi.mail.ru/fcgi-bin/attempt?', params=params) as response:
    #         return await response.json()
    #
    # async def send_second_mobile_code(self, social_account_access_token, session_id):
    #     data = {
    #         "osVersion": f"{random.randint(5, 10)}.{random.randint(0, 10)}.{random.randint(0, 10)}",
    #         "phoneModel": f"{random.choice(('Xiaomi redmi note', 'iphone', 'samsung'))} {random.randint(6, 11)}{random.choice((' PRO', ''))}",
    #         "phoneModelType": "Android",
    #         "phoneNumber": self.phone_number,
    #         "socialAccountAccessToken": social_account_access_token,
    #         "socialAccountId": session_id,
    #         "socialType": "NotifyMailRu",
    #         "uniqueId": self.headers['ur-device-id']
    #     }
    #
    #     async with self._session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/mobile/social",
    #                                  json=data) as response:
    #         pprint(response_json := await response.json())
    #         return response_json
    #
    # async def send_second_mobile_code_to_verify(self, password):
    #     data_get_user_token = {
    #         "client_id": "mobile.client.android",
    #         "client_secret": CLIENT_SECRET,
    #         "username": self.phone_number,
    #         "password": password,
    #         "scope": "bike.api ordering.api location.api customers.api payment.api maintenance.api notification.api log.api ordering.scooter.api driver.bike.lock.offo.api driver.scooter.ninebot.api identity.api offline_access",
    #         "grant_type": "password",
    #     }
    #     rewrite_headers: dict = self.headers.copy()
    #     rewrite_headers.pop('authorization')
    #     async with self._session.post(url="https://service.urentbike.ru/gatewayclient/api/v1/connect/token",
    #                                  headers=rewrite_headers, data=data_get_user_token) as response:
    #         pprint(response_json := await response.json())
    #         self.headers = {**self.headers, **{"authorization": f'Bearer {response_json["access_token"]}'}}
    #         return response_json
