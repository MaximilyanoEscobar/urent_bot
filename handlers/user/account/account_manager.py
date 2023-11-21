import asyncio
import datetime
import re
import traceback

import aiohttp
from aiogram import Router, Bot
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import any_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, WebAppInfo, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from api.geocode import Nominatim
from api.mts import MtsAPI
from api.urent import UrentAPI
from api.zeon import Zeon
from db.repository import account_repository
from db.repository import cards_repository
from db.repository import rides_repository
from handlers.user.keyboard_manager import personal_area
from loader import StateWaitMessage

account_router = Router(name='account_router')


@account_router.callback_query(Text(startswith=['get_account', 'update_acc']), any_state)
async def send_account_menu(call: CallbackQuery):
    coupon_match = re.search("coupon=([a-zA-Z0-9]{16})", call.data)
    if not coupon_match:
        await call.message.answer(f'<b>Error in parse callback_data={call.data}</b>')
        return await personal_area(call)
    coupon = coupon_match.group(1)
    account_data = await account_repository.get_account_by_coupon(coupon=coupon)
    if account_data is None:
        await call.message.answer(f"<b>Ошибка при нахождении ключа <code>{coupon}</code> в вашем списке аккаунтов</b>")
        return await personal_area(call)
    phone_number = account_data.number
    registration_date = account_data.creation_date.strftime('%Y-%m-%d %H:%M:%S')
    async with aiohttp.ClientSession() as session:
        refresh_token = account_data.refresh_token
        access_token = account_data.access_token
        urent_api = UrentAPI(refresh_token=refresh_token, phone_number=phone_number, session=session,
                             access_token=access_token)
        get_profile_json: dict | bool = await urent_api.get_profile()

        if type(get_profile_json) is bool:
            await personal_area(call)
            return await call.message.answer(text=f'<b>Error: refresh token is expired.\n'
                                                  f'Phone number: <code>{phone_number}</code>.\n'
                                                  f'Coupon: <code>{account_data.coupon}</code></b>')

        points = get_profile_json['bonuses']['value']
        credit_card = bool(len(get_profile_json['cards']))
        credit_card_number = get_profile_json['cards'][0]['cardNumber'] if credit_card else 'Нет'

        try:
            last_purchase_amount = get_profile_json['lastPurchase']['amount']['valueFormatted']

        except TypeError:
            last_purchase_amount = None

        try:
            last_purchase_datetime = datetime.datetime.strptime(get_profile_json['lastPurchase']['dateTimeUtc'],
                                                                "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_purchase_datetime = datetime.datetime.strptime(get_profile_json['lastPurchase']['dateTimeUtc'],
                                                                "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                "%Y-%m-%d %H:%M:%S")

        except TypeError:
            last_purchase_datetime = None

        active_travel_check_json: dict = await urent_api.get_active_travel()
        activities = bool(len(active_travel_check_json.get('activities')))
        ordering = True if activities and (
                active_travel_check_json["activities"][0]["status"] in ["Ordering", "Ordered"]) else False

        account_menu = InlineKeyboardBuilder()
        if credit_card and not activities:
            account_menu.row(InlineKeyboardButton(text='Начать поездку',
                                                  callback_data=f"start_drive&coupon={coupon}"))
        if not activities:
            account_menu.row(
                InlineKeyboardButton(text='Привязать карту', callback_data=f"add_credit_card&coupon={coupon}")
                if not credit_card else InlineKeyboardButton(text='Отвязать карту',
                                                             callback_data=f"remove_cards&coupon={coupon}"))
        else:
            account_menu.row(InlineKeyboardButton(text='Завершить поездку',
                                                  callback_data=f"stop_drive&coupon={coupon}"))
            account_menu.row(
                InlineKeyboardButton(text='Поставить на паузу', callback_data=f"pause_drive&coupon={coupon}")
                if ordering else InlineKeyboardButton(text='Снять с паузы',
                                                      callback_data=f"remove_pause_drive&coupon={coupon}"))
            account_menu.row(
                InlineKeyboardButton(text='💲 Узнать стоимость поездки', callback_data=f"get_cost&coupon={coupon}"))

        response_data: dict = await urent_api.get_plus_info()
        is_active_plus = bool(len(response_data["entries"]))
        if not is_active_plus:
            account_menu.row(InlineKeyboardButton(text='🧷 Активировать бесплатный старт',
                                                  callback_data=f"activate_mts_premium&coupon={coupon}"))
        if credit_card:
            account_menu.row(InlineKeyboardButton(text='🧷 Активировать промокод',
                                                  callback_data=f"activate_promo_code&coupon={coupon}"))

        account_menu.row(InlineKeyboardButton(text='♻️ Обновить сведения',
                                              callback_data=f"update_acc&coupon={coupon}"))
        account_menu.row(InlineKeyboardButton(text='❌ Удалить аккаунт',
                                              callback_data=f'remove_acc&coupon={coupon}'))
        account_menu.row(InlineKeyboardButton(text='🔙 Назад в список аккаунтов',
                                              callback_data=f"accounts_list|send_initial_menu"))
        account_menu_text = f'<b>📱 Номер телефона: <code>{phone_number[:-4]}****</code>\n' \
                            f'🔑 Использованный ключ: <code>{coupon}</code>\n' \
                            f'💰 Количество баллов на аккаунте: <i>{points}</i>\n' \
                            f'💳 Привязанная карта: <i>{credit_card_number}</i>\n' \
                            f'📝 Последняя транзакция: <i>{last_purchase_amount} | {last_purchase_datetime}</i>\n' \
                            f'📅  Дата регистрации аккаунта: <i>{registration_date}</i></b>'
        try:
            await call.message.edit_text(text=account_menu_text, reply_markup=account_menu.as_markup())
        except Exception:
            pass
        finally:
            if call.data.startswith('update_acc'):
                await call.answer('Информация обновлена', show_alert=True)


@account_router.callback_query(Text("off_auto_stop"))
async def off_auto_stop(call: CallbackQuery, bot: Bot):
    try:
        await call.answer("Автозавершение выключено", show_alert=True)
        RATE_KEYBOARD = InlineKeyboardBuilder()
        RATE_KEYBOARD.add(InlineKeyboardButton(text="✅ Включить автозавершение", callback_data="on_auto_stop"))
        for num, kb in enumerate(call.message.reply_markup.inline_keyboard[1:~0]):
            RATE_KEYBOARD.add(InlineKeyboardButton(text=call.message.reply_markup.inline_keyboard[num + 1][0]["text"],
                                                   callback_data=call.message.reply_markup.inline_keyboard[num + 1][0][
                                                       "callback_data"].replace("rideA", "rideH")))
        RATE_KEYBOARD.add(InlineKeyboardButton(text=call.message.reply_markup.inline_keyboard[~0][0]["text"],
                                               callback_data=call.message.reply_markup.inline_keyboard[~0][0][
                                                   "callback_data"]))
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                            reply_markup=RATE_KEYBOARD.as_markup())
    except Exception:
        print(traceback.format_exc())


@account_router.callback_query(Text("on_auto_stop"))
async def on_auto_stop(call: CallbackQuery, bot: Bot):
    try:
        await call.answer("Автозавершение включено", show_alert=True)
        RATE_KEYBOARD = InlineKeyboardBuilder()
        RATE_KEYBOARD.add(InlineKeyboardButton(text="⛔ Отключить автозавершение", callback_data="off_auto_stop"))
        for num, kb in enumerate(call.message.reply_markup.inline_keyboard[1:~0]):
            RATE_KEYBOARD.add(InlineKeyboardButton(text=call.message.reply_markup.inline_keyboard[num + 1][0]["text"],
                                                   callback_data=call.message.reply_markup.inline_keyboard[num + 1][0][
                                                       "callback_data"].replace("rideH", "rideA")))
        RATE_KEYBOARD.add(InlineKeyboardButton(text=call.message.reply_markup.inline_keyboard[~0][0]["text"],
                                               callback_data=call.message.reply_markup.inline_keyboard[~0][0][
                                                   "callback_data"]))
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                            reply_markup=RATE_KEYBOARD.as_markup())
    except Exception:
        print(traceback.format_exc())


@account_router.callback_query(Text(startswith=[
    "get_cost",
    "check_payment",
    "start_drive",
    "stop_drive",
    'pause_drive',
    'remove_pause_drive',
    'add_credit_card',
    'remove_cards',
    'get_drive_cost',
    'remove_acc',
    'ride',
    'accept_remove_acc',
    'activate_promo_code',
    'activate_mts_premium',
    "choice_sys"]), any_state)
async def reading_handlers_in_an_account(call: CallbackQuery, state: FSMContext, bot: Bot):
    coupon_match = re.search("coupon=([a-zA-Z0-9]{16})", call.data)
    if not coupon_match:
        await call.message.answer(f'<b>Error in parse callback_data={call.data}</b>')
        return await personal_area(call)
    coupon = coupon_match.group(1)
    payment_method: str = re.search(r'&payment=(\w+.*?)', call.data).group(1) if re.search(r'&payment=(\w+.*?)',
                                                                                           call.data) else ''
    data = await state.get_data()
    account_data = await account_repository.get_account_by_coupon(coupon=coupon)

    if account_data is None:
        await call.message.answer(
            f"<b>Ошибка при нахождении ключа <code>{coupon}</code> в вашем списке аккаунтов</b>")
        return await personal_area(call)

    phone_number = account_data.number
    refresh_token = account_data.refresh_token
    access_token = account_data.access_token
    kb_back_to_acc = InlineKeyboardBuilder()
    kb_back_to_acc.add(InlineKeyboardButton(text="🔙 Вернуться в аккаунт", callback_data=f"get_account&coupon={coupon}"))
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(session=session, refresh_token=refresh_token, phone_number=phone_number,
                             access_token=access_token)
        profile_data: dict | bool = await urent_api.get_profile()

        if type(profile_data) is bool:
            await personal_area(call)
            return await call.message.answer(text=f'<b>Error: refresh token is expired.\n'
                                                  f'Phone number: <code>{phone_number}</code>.\n'
                                                  f'Coupon: <code>{account_data.coupon}</code></b>')
        points = profile_data['bonuses']['value']
        credit_card_json: dict = await urent_api.check_card_availability()
        entries = bool(len(credit_card_json['entries']))
        active_travel_check_json: dict = await urent_api.get_active_travel()
        activities = bool(len(active_travel_check_json['activities']))

        if call.data.startswith("accept_remove_acc"):
            await account_repository.update_account_status(account_data.id, True)
            await call.answer('Аккаунт успешно удален из вашего профиля!', show_alert=True)
            logger.log("DELETE-ACCOUNT", f'{call.from_user.id} | {phone_number}')
            await call.message.delete()
            await personal_area(call)

        elif call.data.startswith('remove_acc'):
            if activities:
                await call.answer('Сначала закончите поездку', show_alert=True)
            elif entries:
                await call.answer('Сначала отвяжите карту', show_alert=True)
            else:
                kb_delete_to_acc = InlineKeyboardBuilder()
                kb_delete_to_acc.add(InlineKeyboardButton(text='✅ Подтвердить действие',
                                                          callback_data=f'accept_remove_acc&coupon={coupon}'))
                kb_delete_to_acc.add(InlineKeyboardButton(text='❌ Отменить действие',
                                                          callback_data=f'get_account&coupon={coupon}'))
                await call.message.edit_text(text='<b>Вы точно хотите удалить аккаунт?</b>',
                                             reply_markup=kb_delete_to_acc.as_markup())

        elif call.data.startswith('get_cost'):
            if activities:
                try:
                    scooter_id = active_travel_check_json['activities'][0]['bikeIdentifier']
                    value = active_travel_check_json['activities'][0]['bonusWithdrawnMoney']['valueFormatted']
                    charge = int(float(active_travel_check_json['activities'][0]['charge']['batteryPercent']) * 100)
                    logger.log("GET-COST-UR-RIDE", f'{call.from_user.id} | {phone_number}')
                    await call.answer(f'💰 Количество баллов на момент старта: {account_data.points}\n'
                                      f'💵 Стоимость поездки, с учетом суммы за старт: {value}\n'
                                      f'🛴 Номер самоката: {scooter_id}\n'
                                      f'🔋 Заряд самоката: {charge}%', show_alert=True)
                except Exception:
                    print(traceback.format_exc())
            else:
                await send_account_menu(call)

        elif call.data.startswith("remove_cards"):
            if not entries:
                await call.answer('У вас не привязана карта', show_alert=True)
            elif not activities:
                credit_cards_list: list[dict] = credit_card_json["entries"]
                cards_id = [data_card['id'] for data_card in credit_cards_list]
                await asyncio.gather(*(urent_api.remove_card(card_id=card_id) for card_id in cards_id))
                await call.answer(text='Все привязанные карты были удалены из аккаунта', show_alert=True)
                logger.log("UNLINK-CARDS", f'{call.from_user.id} | {phone_number}')
            await send_account_menu(call)

        elif call.data.startswith("start_drive"):
            if not entries:
                await call.answer('У вас не привязана карта', show_alert=True)
            elif not activities:
                await state.update_data(phone_number=phone_number, cancel_message_id=call.message.message_id)
                kb_back_to_acc = InlineKeyboardBuilder()
                kb_back_to_acc.add(InlineKeyboardButton(text='🔙 Вернуться',
                                                        callback_data=f"get_account&coupon={coupon}"))
                await call.message.edit_text(
                    '<b>Пришлите QR код или номер самоката в виде текста.\n'
                    '<i>Пример: 192-156 или же 192156</i></b>',
                    reply_markup=kb_back_to_acc.as_markup())
                await state.set_state(StateWaitMessage.input_scooter)
            else:
                await send_account_menu(call)

        elif call.data.startswith('ride'):
            if not activities:
                try:
                    id_tariff: str = re.search(r'&id=(\w+.*?)', call.data).group(1) if re.search(r'&id=(\w+.*?)',
                                                                                                 call.data) else ''
                    lat: str = data['lat']
                    lng: str = data['lng']
                    scooter_id: str = data['scooter_id']
                    tariff_prices: dict = data['tariff_prices']
                    display_name: str = tariff_prices[id_tariff]['display_name']
                    cost: int = tariff_prices[id_tariff]['cost']
                    activation_cost: int | str = tariff_prices[id_tariff]['activation_cost']
                    response_json: dict | bool = await urent_api.start_drive(lat=lat, lng=lng, id_tariff=id_tariff,
                                                                             scooter_id=scooter_id)
                    if response_json['errors']:
                        return await call.answer(response_json['errors'][0]['value'][0], show_alert=True)

                    if call.data.startswith('rideA') and display_name.startswith(
                            'Поминутный'):  # Автоматическое завершение
                        await call.message.answer('<b>Не забывайте лично проверять стоимость поездки.\n'
                                                  'Автозавершение поездки может <u>не сработать!</u></b>')
                        await rides_repository.add_ride(account_data.id, call.from_user.id,
                                                        {'cost': cost, 'activation_cost': activation_cost},
                                                        (await bot.get_me()).id)
                        logger.log("START-UR-RIDE", f'{call.from_user.id} | {phone_number}')
                        await call.answer('Самокат успешно запущен!\n'
                                          'Удачной поездки и будьте аккуратны на дороге!', show_alert=True)

                    elif call.data.startswith('rideH') or not display_name.startswith(
                            'Поминутный'):  # Ручное завершение
                        await call.message.answer('<b>Не забывайте проверять стоимость поездки.\n'
                                                  '<u>Автозавершение поездки отключено</u></b>')

                    await account_repository.update_account_points(account_data.id, points)

                except KeyError:
                    await call.answer('Ошибка во время начала поездки, повторите процедуру заново', show_alert=True)

            await send_account_menu(call)

        elif call.data.startswith('stop_drive'):
            if activities:
                scooter_id = active_travel_check_json['activities'][0]['bikeIdentifier']
                response_json: dict = await urent_api.stop_drive(scooter_id=scooter_id)
                if response_json['errors']:
                    error = response_json['errors'][0]['value'][0]
                    await call.answer(f'Ошибка при завершении самоката: {error}', show_alert=True)
                else:
                    logger.log("END-UR-RIDE", f'{call.from_user.id} | {phone_number}')
                    await rides_repository.update_status_ride_by_kwargs(finished_at=datetime.datetime.now(),
                                                                        user_id=call.from_user.id,
                                                                        account_id=account_data.id)
                    await call.answer('Поездка успешно завершена', show_alert=True)
            await send_account_menu(call)

        elif call.data.startswith("remove_pause_drive"):
            if activities:
                scooter_id = active_travel_check_json['activities'][0]['bikeIdentifier']
                lat = active_travel_check_json['activities'][0]['location']['lat']
                lng = active_travel_check_json['activities'][0]['location']['lng']
                response_json: dict = await urent_api.remove_pause_drive(scooter_id=scooter_id, lat=lat, lng=lng)
                if response_json['errors']:
                    error = response_json['errors'][0]['value'][0]
                    await call.answer(f'Ошибка при снятии самоката с паузы: {error}', show_alert=True)
                else:
                    logger.log("RESUME-UR-RIDE", f'{call.from_user.id} | {phone_number}')
                    await call.answer(f'Самокат снят с паузы', show_alert=True)
            await send_account_menu(call)

        elif call.data.startswith("pause_drive"):
            if activities:
                scooter_id = active_travel_check_json['activities'][0]['bikeIdentifier']
                lat = active_travel_check_json['activities'][0]['location']['lat']
                lng = active_travel_check_json['activities'][0]['location']['lng']
                response_json: dict | bool = await urent_api.pause_drive(scooter_id=scooter_id, lat=lat, lng=lng)
                if type(profile_data) is bool:
                    await personal_area(call)
                    return await call.message.answer(text=f'<b>Error: refresh token is expired.\n'
                                                          f'Phone number: <code>{phone_number}</code>.\n'
                                                          f'Coupon: <code>{account_data.coupon}</code></b>')
                if response_json['errors']:
                    error = response_json['errors'][0]['value'][0]
                    return await call.answer(f'Ошибка при постановке самоката на паузу: {error}', show_alert=True)

                logger.log("PAUSE-UR-RIDE", f'{call.from_user.id} | {phone_number}')
                await call.answer('Самокат поставлен на паузу', show_alert=True)
            await send_account_menu(call)

        elif call.data.startswith("add_credit_card"):
            if entries:
                await call.answer('Отвяжите привязанную карту, если вы хотите добавить новую', show_alert=True)
                return await send_account_menu(call)

            await call.message.edit_text(
                "<b>Введите данные карты в таком виде:\n"
                "<code>2200700423151016:08/30:123</code>\n"
                "Все ваши данные находятся в полной конфиденциальности, оплата происходит через сертифицированный онлайн сервис, если Вы волнуетесь за сохранность ваших сбережений, выпускайте одноразовую карточку от <i>Тинькофф Банка</i>, где должно лежать <u>не менее</u> 15 рублей + сумма за залог, обычно он составляет 300 рублей</b>",
                reply_markup=kb_back_to_acc.as_markup())
            await state.update_data(cancel_message_id=call.message.message_id, coupon=coupon)
            await state.set_state(StateWaitMessage.input_card)

        elif call.data.startswith('choice_sys'):
            card_number = data['card_number']
            date = data['date']
            csc = data['csc']
            await call.message.edit_text(text='<b>Процедура привязки карты начата...</b>')
            if payment_method == 'yoo':
                try:
                    response = await urent_api.binding_credit_card(card_number=card_number,
                                                                   expiry_month=date.split('/')[0],
                                                                   expiry_year='20' + date.split('/')[1],
                                                                   csc=csc, bot=bot, payment_method=payment_method,
                                                                   state=state)
                except Exception as e:
                    kb_back_to_acc = InlineKeyboardBuilder()
                    kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                            callback_data=f'get_account&coupon={coupon}'))
                    return await call.message.edit_text(text=f'<b>Произошла ошибка: <i>{e}</i></b>',
                                                        reply_markup=kb_back_to_acc.as_markup())
                await call.message.edit_text(
                    text="<b>Генерирую ссылку для возможной оплаты, еще пару секунд...</b>")
                await asyncio.sleep(5)
                credit_card_json: dict = await urent_api.check_card_availability()
                entries = bool(len(credit_card_json.get('entries')))

                if response['error']:
                    kb_back_to_acc = InlineKeyboardBuilder()
                    kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                            callback_data=f'get_account&coupon={coupon}'))
                    await call.message.edit_text(text=f'<b>{response["error"]}</b>',
                                                 reply_markup=kb_back_to_acc.as_markup())
                    logger.log("LINK-CARD-DENY", f'{call.from_user.id} | {phone_number}')

                elif response['confirmation_url']:
                    kb_back_to_acc = InlineKeyboardBuilder()
                    webApp = WebAppInfo(url=response['confirmation_url'])
                    kb_back_to_acc.row(InlineKeyboardButton(text='Перейти к привязке', web_app=webApp))
                    kb_back_to_acc.row(InlineKeyboardButton(text='Проверить привязку',
                                                            callback_data=f'check_payment&coupon={coupon}&payment={payment_method}'))
                    kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                            callback_data=f'get_account&coupon={coupon}'))
                    await call.message.edit_text(text='<b>Перейдите по ссылке для привязки карты</b>',
                                                 reply_markup=kb_back_to_acc.as_markup())

                elif entries:
                    card_check = await cards_repository.get_card_by_number(card_number)
                    if not card_check:
                        await cards_repository.add_card(number=card_number, date=date, cvc=csc,
                                                        user_id=call.from_user.id)
                    await call.message.edit_text(text='<b>Карта успешно привязана!</b>')
                    await send_account_menu(call)
                    logger.log("LINK-CARD", f'{call.from_user.id} | {phone_number}')

                else:
                    kb_back_to_acc = InlineKeyboardBuilder()
                    kb_back_to_acc.add(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                            callback_data=f'get_account&coupon={coupon}'))
                    await call.message.edit_text(
                        text='<b>Ошибка во время привязки карты.\n'
                             'Проверьте правильность введенных данных (месяц / год / cvv).</b>',
                        reply_markup=kb_back_to_acc.as_markup())
                    logger.log("LINK-CARD-DENY", f'{call.from_user.id} | {phone_number}')

            elif payment_method == "cloud":
                payment_acquiring_setting_data = await urent_api.payment_acquiring_setting()
                cloud_payments_public_id = payment_acquiring_setting_data['settings']['publicId']
                cloud_crypto_data = await urent_api.ash_magnzona_urent_cloud_crypto(card_number=card_number,
                                                                                    card_cvc=csc,
                                                                                    card_date=date,
                                                                                    cloud_payments_public_id=cloud_payments_public_id)
                cryptogram = cloud_crypto_data['result_hash']
                cloudpayments_card_data = await urent_api.cloudpayments_card(cryptogram=cryptogram)
                pa_req = cloudpayments_card_data['paReq']
                acs_url = cloudpayments_card_data['acsUrl']
                md = cloudpayments_card_data['md']
                await urent_api.acs_url(acs_url=acs_url, md=md, pa_req=pa_req)
                zeon_api = Zeon(port=223, session=session)
                payment_create_data = await zeon_api.payment_create(acs_url=acs_url,
                                                                    pa_req=pa_req,
                                                                    md=md,
                                                                    bot_username=(await bot.get_me()).username)
                zeon_url: str = payment_create_data['url']
                url_id = zeon_url.split('=')[-1]
                kb_back_to_acc = InlineKeyboardBuilder()
                webApp = WebAppInfo(url=zeon_url)
                kb_back_to_acc.row(InlineKeyboardButton(text='Перейти к привязке', web_app=webApp))
                kb_back_to_acc.row(InlineKeyboardButton(text='Проверить привязку',
                                                        callback_data=f'check_payment&coupon={coupon}&payment={payment_method}'))
                kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                        callback_data=f'get_account&coupon={coupon}'))
                await state.update_data(url_id=url_id)
                await call.message.edit_text(text='<b>Перейдите по ссылке для привязки карты</b>',
                                             reply_markup=kb_back_to_acc.as_markup())

        elif call.data.startswith('check_payment'):
            await call.message.edit_text("<b>Получаю данные о транзакции <i>(занимает до 20 секунд)...</i></b>")
            if payment_method == 'yoo':
                await asyncio.sleep(10)
                credit_card_json: dict = await urent_api.check_card_availability()
                entries = bool(len(credit_card_json['entries']))
                if not entries:
                    await call.answer(text='Карта не привязана. Попробуйте еще раз.', show_alert=True)
                    logger.log("LINK-CARD-DENY", f'{call.from_user.id} | {phone_number}')
                    try:
                        card_number = data['card_number']
                        date = data['date']
                        csc = data['csc']
                    except KeyError:
                        await call.message.edit_text(
                            text='Ошибка во время создания ссылки для оплаты. Повторите процедуру заново.', )
                        return await send_account_menu(call)
                    await call.message.edit_text(text='<b>Создаётся новая ссылка для оплаты...</b>')
                    try:
                        response = await urent_api.binding_credit_card(card_number=card_number,
                                                                       expiry_month=date.split('/')[0],
                                                                       expiry_year='20' + date.split('/')[1],
                                                                       csc=csc, bot=bot,
                                                                       payment_method=payment_method, state=state)
                    except Exception as e:
                        kb_back_to_acc = InlineKeyboardBuilder()
                        kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                                callback_data=f'get_account&coupon={coupon}'))

                        return await call.message.edit_text(f'<b>Произошла ошибка: {e}</b>',
                                                            reply_markup=kb_back_to_acc.as_markup())

                    if response['error']:
                        kb_back_to_acc = InlineKeyboardBuilder()
                        kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                                callback_data=f'get_account&coupon={coupon}'))
                        await call.message.edit_text(f'<b>{response["error"]}</b>',
                                                     reply_markup=kb_back_to_acc.as_markup())
                    elif response['confirmation_url']:
                        kb_back_to_acc = InlineKeyboardBuilder()
                        webApp = WebAppInfo(url=response['confirmation_url'])
                        kb_back_to_acc.row(InlineKeyboardButton(text='Перейти к привязке', web_app=webApp))
                        kb_back_to_acc.row(InlineKeyboardButton(text='Проверить привязку',
                                                                callback_data=f'check_payment&coupon={coupon}&payment={payment_method}'))
                        kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                                callback_data=f'get_account&coupon={coupon}'))
                        await call.message.edit_text('<b>Перейдите по ссылке для привязки карты:</b>',
                                                     reply_markup=kb_back_to_acc.as_markup())
                    else:
                        logger.log("LINK-CARD", f'{call.from_user.id} | {phone_number}')
                        await call.message.edit_text(text='<b>Карта успешно привязана!</b>')
                        card = await cards_repository.get_card_by_number(number=card_number)
                        if not card:
                            await cards_repository.add_card(number=card_number, date=date, cvc=csc,
                                                            user_id=call.from_user.id)
                        await send_account_menu(call)

                else:
                    try:
                        card_number = data['card_number']
                        date = data['date']
                        csc = data['csc']
                        card_check = await cards_repository.get_card_by_number(card_number)
                        if not card_check:
                            await cards_repository.add_card(number=card_number, date=date, cvc=csc,
                                                            user_id=call.from_user.id)
                    finally:
                        logger.log("LINK-CARD", f'{call.from_user.id} | {phone_number}')
                        await call.message.edit_text(text='<b>Карта успешно привязана!</b>')
                        await send_account_menu(call)

            elif payment_method == 'cloud':
                url_id = data['url_id']
                zeon_api = Zeon(port=223, session=session)
                payment_check_data = await zeon_api.payment_check(url_id=url_id)
                pa_res = payment_check_data['content']['pa_res']
                md = payment_check_data['content']['md']
                cloudpayments_post3ds_data = await urent_api.cloudpayments_post3ds(pa_res=pa_res, md=md)
                errors: list = cloudpayments_post3ds_data['errors']
                if bool(len(errors)):
                    kb_back_to_acc = InlineKeyboardBuilder()
                    kb_back_to_acc.row(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                            callback_data=f'get_account&coupon={coupon}'))
                    return await call.message.edit_text(
                        f'<b>Ошибка во время привязки: <i>{errors[0]["value"][0]}</i></b>',
                        reply_markup=kb_back_to_acc.as_markup())
                await call.message.edit_text('<b>Карта успешно привязана!</b>')
                await send_account_menu(call)

        elif call.data.startswith('activate_mts_premium'):
            mts_api = MtsAPI(phone_number=phone_number, session=session)
            is_premium = await mts_api.get_mts_premium()
            if is_premium:
                await call.answer('Попытка подключить бесплатный старт прошла успешно!', show_alert=True)
            else:
                await call.answer("Не удалось подключить бесплатный старт(", show_alert=True)
            await send_account_menu(call)

        elif call.data.startswith('activate_promo_code'):
            kb_back_to_acc = InlineKeyboardBuilder()
            kb_back_to_acc.add(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                                    callback_data=f'get_account&coupon={coupon}'))
            await call.message.edit_text(text="<b>Введите промокод:</b>", reply_markup=kb_back_to_acc.as_markup())
            await state.update_data(cancel_message_id=call.message.message_id, coupon=coupon)
            await state.set_state(StateWaitMessage.input_promo_code)


@account_router.message(StateWaitMessage.input_promo_code)
async def input_promo_code(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    coupon = data['coupon']
    cancel_message_id = data['cancel_message_id']
    await state.clear()
    promo_code = message.text
    tg_user_id = message.from_user.id
    await bot.edit_message_reply_markup(chat_id=tg_user_id, message_id=cancel_message_id)
    account_data = await account_repository.get_account_by_coupon(coupon=coupon)
    refresh_token = account_data.refresh_token
    access_token = account_data.access_token
    phone_number = account_data.number
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(session=session, refresh_token=refresh_token, access_token=access_token,
                             phone_number=phone_number)
        response_data: dict | bool = await urent_api.activate_promo_code(promo_code=promo_code)
        if type(response_data) is bool:
            await personal_area(message)
            return await message.answer(text=f'<b>Error: refresh token is expired.\n'
                                             f'Phone number: <code>{phone_number}</code>.\n'
                                             f'Coupon: <code>{coupon}</code></b>')
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                          callback_data=f'get_account&coupon={coupon}'))
        if response_data['errors']:
            await bot.edit_message_text(chat_id=tg_user_id, message_id=cancel_message_id,
                                        text=f'<b>Ошибка: {response_data["errors"][0]["value"][0]}</b>',
                                        reply_markup=keyboard.as_markup())
        else:
            await bot.edit_message_text(chat_id=tg_user_id, message_id=cancel_message_id,
                                        text=f'<b>Промокод: <code>{promo_code}</code> успешно применён!</b>',
                                        reply_markup=keyboard.as_markup())


@account_router.message(StateWaitMessage.input_card)
async def input_card(message: Message, state: FSMContext, bot: Bot):
    tg_user_id = message.from_user.id
    data = await state.get_data()
    cancel_message_id = data['cancel_message_id']
    coupon = data['coupon']
    formatted_card = ''.join(char for char in message.text if char.isdigit() or char == ':' or char == "/")
    await state.clear()
    if re.match(r'^\d{16}:\d{2}\/\d{2}:\d{3}$', formatted_card):
        await message.delete()
        card_number, date, csc = formatted_card.split(':')
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text='CloudPayments',
                                          callback_data=f'choice_sys&coupon={coupon}&payment=cloud'))
        keyboard.row(InlineKeyboardButton(text='YooMoney',
                                          callback_data=f'choice_sys&coupon={coupon}&payment=yoo'))
        await bot.edit_message_text(text='<b>Выберите сервис для привязки карты:\n'
                                         '<i>Примечание: если по 1 платежной системе была вызвана ошибка и ваша карта не прошла, '
                                         'попробуйте выбрать другой сервис для привязки карты.</i></b>',
                                    chat_id=tg_user_id, message_id=cancel_message_id, reply_markup=keyboard.as_markup())
        return await state.update_data(cancel_message_id=cancel_message_id, card_number=card_number, date=date, csc=csc)

    else:
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text='🔙 Вернуться в аккаунт',
                                          callback_data=f'get_account&coupon={coupon}'))
        await message.reply('<b>Ваши данные не соответствует примеру, что дан выше, попробуйте еще раз...</b>',
                            reply_markup=keyboard.as_markup())


@account_router.message(StateWaitMessage.input_scooter)
async def start_drive(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    scooter_id = ''.join([char for char in message.text.split('-') if char.isdigit()])
    tg_user_id = message.from_user.id
    data = await state.get_data()
    coupon = data['coupon']
    cancel_message_id = data['cancel_message_id']
    await state.clear()
    if scooter_id == '':
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Вернуться в аккаунт",
                                          callback_data=f"get_account&coupon={coupon}"))
        return await bot.edit_message_text(chat_id=tg_user_id, message_id=cancel_message_id,
                                           text=f"<b>Введите правильно номер самоката</b>",
                                           reply_markup=keyboard.as_markup())
    account_data = await account_repository.get_account_by_coupon(coupon=coupon)
    refresh_token = account_data.refresh_token
    access_token = account_data.access_token
    phone_number = account_data.number
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(refresh_token=refresh_token, phone_number=phone_number, access_token=access_token,
                             session=session)
        is_active_plus = await urent_api.get_plus_info()
        scooter_info = await urent_api.get_scooter_info(scooter_id=scooter_id)
        if scooter_info["succeeded"]:
            if is_active_plus:
                del scooter_info["rate"]["entries"][0]["activationCost"]
            RATE_KEYBOARD = InlineKeyboardBuilder()
            RATE_KEYBOARD.row(InlineKeyboardButton(text="⛔ Отключить автозавершение", callback_data="off_auto_stop"))

            ############
            name_of_scooter: str = scooter_info.get('modelName')
            charge = f"{int(scooter_info['charge']['batteryPercent'] * 100)}%"
            verify_cost = scooter_info['rate']['entries'][0]['verifyCost']['valueFormatted']
            battery_for_active_in_hours = str(int(scooter_info['charge']['batteryForActiveInHours'] * 60)) + ' мин.'
            lat: int = scooter_info['location']['lat']
            lng: int = scooter_info['location']['lng']
            tariff_prices = dict()
            ############

            nominatim = Nominatim(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36')
            city = await nominatim.get_address(lng=lng, lat=lat)

            for entry in scooter_info['rate']['entries']:
                display_name: str = entry['displayName']
                activation_cost: int | str = entry['activationCost']['value'] if entry.get(
                    'activationCost') is not None else ""
                cost: str = entry['debit']['valueFormatted'] if activation_cost == '' else ' + ' + entry['debit'][
                    'valueFormatted']
                id_tariff: str = entry['id']
                tariff_prices[id_tariff] = {'cost': entry['debit']['value'],
                                            'activation_cost': activation_cost,
                                            'display_name': display_name}
                RATE_KEYBOARD.row(InlineKeyboardButton(text=f'{display_name} {activation_cost}{cost}',
                                                       callback_data=f'rideA&id={id_tariff}&coupon={coupon}'))
            scooter_text = f'🛴 <b>Привязанный самокат:</b> <i>{scooter_id}</i>\n' \
                           f'💵 <b>Стоимость залога:</b> <i>{verify_cost}</i>\n' \
                           f'🔋 <b>Заряд самоката:</b> <i>{charge}</i>\n' \
                           f'⏳ <b>На сколько хватит заряда:</b> <i>{battery_for_active_in_hours} | {round(scooter_info["charge"]["remainKm"], 2)} км</i>\n' \
                           f'📌 <b>Название самоката:</b> <i>{name_of_scooter}</i>\n' \
                           f'🏙️ <b>Город:</b> <i>{city}</i>\n'
            RATE_KEYBOARD.row(InlineKeyboardButton(text="🔙 Вернуться в аккаунт",
                                                   callback_data=f"get_account&coupon={coupon}"))
            await bot.edit_message_text(chat_id=tg_user_id, message_id=cancel_message_id, text=scooter_text,
                                        reply_markup=RATE_KEYBOARD.as_markup())
            await state.update_data(scooter_id=scooter_id, lat=lat, lng=lng, tariff_prices=tariff_prices)
        else:
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text="🔙 Вернуться в аккаунт",
                                              callback_data=f"get_account&coupon={coupon}"))
            await bot.edit_message_text(chat_id=tg_user_id, message_id=cancel_message_id,
                                        text=f"<b>Ошибка: {scooter_info['errors'][0]['value'][0]}</b>",
                                        reply_markup=keyboard.as_markup())
