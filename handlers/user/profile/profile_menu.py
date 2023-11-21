import aiohttp
from aiogram import Router, Bot
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import any_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.host import Host
from api.urent import UrentAPI
from db.repository import account_repository
from loader import StateWaitMessage
from utils.paginator import Paginator

profile_router = Router(name="profile_router")


@profile_router.callback_query(Text('add_personal_account'))
async def add_personal_account(call: CallbackQuery, state: FSMContext):
    kb_back_to_account_list = InlineKeyboardBuilder()
    kb_back_to_account_list.row(InlineKeyboardButton(text='Вернуться в список аккаунтов', callback_data='accounts_list|send_initial_menu'))
    message = await call.message.edit_text(text='<b>Пришлите номер телефона:</b>', reply_markup=kb_back_to_account_list.as_markup())
    await state.set_state(StateWaitMessage.input_phone_number)
    await state.update_data(cancel_message_id=message.message_id)


@profile_router.message(StateWaitMessage.input_phone_number)
async def input_phone_number(message: Message, state: FSMContext, bot: Bot):
    cancel_message_id = (await state.get_data())['cancel_message_id']
    phone_number = message.text
    await state.clear()
    await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=cancel_message_id)
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(session=session, phone_number=phone_number)
        verify_phone_data = await urent_api.ash_magnzona_urent_verify_phone()
        system_id = verify_phone_data["request_params"]["system_id"]
        device_id = verify_phone_data["request_params"]["device_id"]
        session_id = verify_phone_data["request_params"]["session_id"]
        full_url = verify_phone_data["full_url"]
        full_url_data = await urent_api.full_url(full_url=full_url)
        verification_url = full_url_data['verification_url']
        social_id = full_url_data['session_id']

        if verification_url == "":
            return message.reply('<b>Не удалось отправить смс-код на ваш номер телефона</b>')

        kb_back_to_account_list = InlineKeyboardBuilder()
        kb_back_to_account_list.row(InlineKeyboardButton(text='Вернуться в список аккаунтов', callback_data='accounts_list|send_initial_menu'))
        message_data = await message.reply('<b>Введите смс-код, отправленный на ваш номер телефона</b>', reply_markup=kb_back_to_account_list.as_markup())
        await state.set_state(StateWaitMessage.input_sms_code)
        await state.update_data(system_id=system_id,
                                device_id=device_id,
                                session_id=session_id,
                                social_id=social_id,
                                phone_number=phone_number,
                                cancel_message_id=message_data.message_id)


@profile_router.message(StateWaitMessage.input_sms_code)
async def input_sms_code(message: Message, state: FSMContext, bot: Bot):
    sms_code = message.text
    state_data = await state.get_data()
    await state.clear()
    system_id = state_data["system_id"]
    device_id = state_data["device_id"]
    session_id = state_data["session_id"]
    social_id = state_data["social_id"]
    phone_number = state_data["phone_number"]
    cancel_message_id = state_data['cancel_message_id']
    await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=cancel_message_id)
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(session=session, phone_number=phone_number)
        urent_attempt_data = await urent_api.ash_magnzona_urent_attempt(sms_code=sms_code, session_id=session_id)
        full_url = urent_attempt_data['full_url']
        full_url_data = await urent_api.full_url(full_url=full_url)
        attempt_token = full_url_data['token']
        if attempt_token == "":
            return message.reply('<b>Не удалось валидировать смс-код</b>')
        mobile_social_data = await urent_api.mobile_social(attempt_token=attempt_token, system_id=system_id, social_id=social_id)
        sms_auto_code = mobile_social_data['smsAutoCode']
        connect_token_data = await urent_api.connect_token(device_id=device_id, session_id=session_id, system_id=system_id, sms_auto_code=sms_auto_code)
        if connect_token_data.get('error_description'):
            return message.reply(f'<b>{connect_token_data["error_description"]}</b>')
        access_token = connect_token_data['access_token']
        refresh_token = connect_token_data['refresh_token']
        host_api = Host(port_server=8080, session=session)
        upload_account_data = await host_api.upload_account(phone_number=phone_number, access_token=access_token, refresh_token=refresh_token, count_bonus=0)
        coupon = upload_account_data['coupon']
        account_data = await account_repository.get_account_by_coupon(coupon=coupon)
        if account_data is not None and account_data.user_id is None:
            await account_repository.update_account_user_id(account_data.id, user_id=message.from_user.id)
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text='Перейти к аккаунту',
                                              callback_data=f'get_account&coupon={coupon}'))
            return message.reply('<b>Вы успешно вошли в свой аккаунт!</b>', reply_markup=keyboard.as_markup())


@profile_router.callback_query(Text(startswith=['accounts_list']), any_state)
async def send_accounts_list_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    tg_user_id = call.from_user.id
    accounts_list = await account_repository.get_accounts_by_user_id(tg_user_id)
    if bool(len(accounts_list)):
        if call.data.split('|')[1].startswith('send_initial_menu'):
            paginator = Paginator(accounts_list)
            keyboard = await paginator.generate_accounts_list_keyboard()
            await call.message.edit_text(f'<b>Ваш список аккаунтов:</b>', reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('page_back'):
            if int(call.data.split('&page=')[1]) > 0:
                paginator = Paginator(accounts_list)
                keyboard = await paginator.generate_accounts_list_keyboard(int(call.data.split('&page=')[1]) - 1)
                await call.message.edit_text(f'<b>Ваш список аккаунтов:</b>', reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('page_now'):
            await call.answer(f"Вы находитесь на странице: {int(call.data.split('&page=')[1]) + 1}", show_alert=True)

        elif call.data.split('|')[1].startswith('page_next'):
            now_page = int(call.data.split('&page=')[1]) if len(accounts_list) / 4 > 1 else int(
                call.data.split('&page=')[1]) + 1
            if now_page < len(accounts_list) // 4:
                paginator = Paginator(accounts_list)
                keyboard = await paginator.generate_accounts_list_keyboard(int(call.data.split('&page=')[1]) + 1)
                await call.message.edit_text(f'<b>Ваш список аккаунтов:</b>', reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('send_activation_date'):
            await call.answer(f"Время активации: {call.data.split('&date=')[1]}", show_alert=True)

    else:
        await call.answer('Список аккаунтов пуст :(\n'
                          'Давай исправим это ?', show_alert=True)


@profile_router.callback_query(Text(startswith=['purchase_history']), any_state)
async def send_purchase_history_menu(call: CallbackQuery):
    tg_user_id = call.from_user.id
    accounts_deleted = await account_repository.get_accounts_by_user_id(user_id=tg_user_id, is_delete=True)
    accounts_not_deleted = await account_repository.get_accounts_by_user_id(user_id=tg_user_id)
    list_of_purchases = accounts_deleted + accounts_not_deleted
    if bool(len(list_of_purchases)):
        if call.data.split('|')[1].startswith('send_initial_menu'):
            paginator = Paginator(list_of_purchases)
            keyboard = await paginator.generate_purchase_list_keyboard()
            await call.message.edit_text(f'<b>История последних {len(list_of_purchases)} активаций:</b>',
                                         reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('page_back'):
            if int(call.data.split('&page=')[1]) > 0:
                paginator = Paginator(list_of_purchases)
                keyboard = await paginator.generate_purchase_list_keyboard(int(call.data.split('&page=')[1]) - 1)
                await call.message.edit_text(f'<b>История последних {len(list_of_purchases)} активаций:</b>',
                                             reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('page_now'):
            await call.answer(f"Вы находитесь на странице: {int(call.data.split('&page=')[1]) + 1}", show_alert=True)

        elif call.data.split('|')[1].startswith('page_next'):
            if int(call.data.split('&page=')[1]) < len(list_of_purchases) // 4:
                paginator = Paginator(list_of_purchases)
                keyboard = await paginator.generate_purchase_list_keyboard(int(call.data.split('&page=')[1]) + 1)
                await call.message.edit_text(f'<b>История последних {len(list_of_purchases)} активаций:</b>',
                                             reply_markup=keyboard.as_markup())

        elif call.data.split('|')[1].startswith('send_activation_date'):
            await call.answer(f"Время активации: {call.data.split('&date=')[1]}", show_alert=True)

    else:
        await call.answer('Список активаций пуст :(\nДавай исправим это ?', show_alert=True)
