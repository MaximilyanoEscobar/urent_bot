import asyncio
import os
import re

import aiofiles
import aiohttp
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import any_state
from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.urent import UrentAPI
from data.keyboards import CANCEL_KEYBOARD
from db import Accounts
from db.repository import user_repository, account_repository
from loader import *


admin_router = Router(name="admin_router")


@admin_router.callback_query(F.text == "cancel", any_state)
async def cancel_action(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(call.message.text)
    await state.clear()


@admin_router.message(Command(commands=['admin']))
async def admin_menu(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Лог ключа', callback_data='log_key'))
    keyboard.row(InlineKeyboardButton(text='Открыть аккаунт', callback_data='open_account'))
    keyboard.row(InlineKeyboardButton(text='Лог человека', callback_data='log_user'))
    # keyboard.row(InlineKeyboardButton(text='Возобновить ключ', callback_data='refresh_coupon'))
    # keyboard.row(InlineKeyboardButton(text='Возобновить все личные аккаунты', callback_data='refresh_all_accounts'))
    # keyboard.row(InlineKeyboardButton(text="Urent | Выгрузить удаленные аккаунты в виде .txt", callback_data='upload_used_accounts'))

    count_users_in_tg_bot = await user_repository.select_all_users()
    await message.answer(f'<b>Успешный вход в админ панель!\n'
                         f'Количество людей в боте: <i>{len(count_users_in_tg_bot)}</i></b>',
                         reply_markup=keyboard.as_markup())


@admin_router.callback_query(F.data == 'refresh_coupon')
async def refresh_coupon(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(text='<b>Введите ключ, который вы хотите возобновить</b>')
    await state.set_state(StateWaitMessage.input_coupon_to_refresh)


@admin_router.message(StateWaitMessage.input_coupon_to_refresh)
async def input_coupon_to_refresh(message: Message, state: FSMContext):
    await state.clear()
    account = await account_repository.get_account_by_coupon(coupon=message.text)
    if not account:
        return await message.reply('<b>Такой ключ отсутствует в базе</b>')
    await account_repository.update_account_status(account.id, False)
    await message.reply('<b>Ключ успешно возобновлен</b>')


@admin_router.callback_query(F.data == 'refresh_all_accounts')
async def refresh_all_accounts(call: CallbackQuery):
    await call.message.edit_text(text='<b>Процесс восстановления аккаунтов начат. Ожидайте.</b>')
    accounts = await account_repository.get_accounts_by_user_id(user_id=call.from_user.id, is_delete=True)
    task_list = [asyncio.create_task(account_repository.update_account_status(account.id, False)) for account in accounts]
    await asyncio.gather(*task_list)
    await call.message.edit_text(text='<b>Все аккаунты были восстановлены!</b>')


@admin_router.callback_query(lambda call: call.data.startswith('upload_used_accounts'))
async def upload_used_accounts(call: CallbackQuery):
    await call.message.edit_text(text='<b>Начинаю выгрузку всех использованных аккаунтов</b>')
    accounts = await account_repository.get_accounts() + await account_repository.get_accounts(is_delete=False)
    async with aiofiles.open(f'temp/{call.from_user.id}_upload_accounts.txt', 'w+') as file:
        tasks_list = [asyncio.create_task(refresh_token_by_account(account=account, file=file)) for account in accounts]
        await asyncio.gather(*tasks_list)

    tokens_file = FSInputFile(f'temp/{call.from_user.id}_upload_accounts.txt')
    await call.message.answer_document(document=tokens_file)
    os.remove(f'temp/{call.from_user.id}_upload_accounts.txt')


async def refresh_token_by_account(account: Accounts, file):
    refresh_token = account.refresh_token
    access_token = account.access_token
    phone_number = account.number
    async with aiohttp.ClientSession() as session:
        urent_api = UrentAPI(session=session, refresh_token=refresh_token, access_token=access_token,
                             phone_number=phone_number)
        profile_data: dict | bool = await urent_api.get_profile()
        if type(profile_data) is bool:
            return
        points = float(profile_data['bonuses']['value'])
        if 0 <= points <= 50:
            while True:
                try:
                    await account_repository.update_account_status(account.id)
                    break
                except:
                    pass
            return await file.write(f'{phone_number}:{access_token}:{refresh_token}\n')



@admin_router.callback_query(F.data == "open_account")
async def input_coupon_account(call: CallbackQuery, state: FSMContext):
    await state.set_state(StateWaitMessage.input_coupon_account_for_log)
    await call.message.edit_text(text="<b>Введите ключ | id человека для открытия аккаунта: </b>",
                                 reply_markup=CANCEL_KEYBOARD.as_markup())
    await state.update_data(cancel_message_id=call.message.message_id)


@admin_router.message(StateWaitMessage.input_coupon_account_for_log)
async def open_kb_account(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cancel_message_id = data['cancel_message_id']
    await state.clear()
    if message.text.isdigit():
        accounts_list = await account_repository.get_accounts_by_user_id(int(message.text))
    else:
        accounts_list = await account_repository.get_account_by_coupon(message.text)
    await message.delete()
    if not accounts_list:
        return await bot.edit_message_text(text="Аккаунты не найдены!", message_id=cancel_message_id,
                                           chat_id=message.from_user.id)
    keyboard = InlineKeyboardBuilder()
    try:
        iter(accounts_list)
    except Exception:
        accounts_list = [accounts_list]
    for account in accounts_list:
        keyboard.row(InlineKeyboardButton(text=f'{account.number}',
                                          callback_data=f'get_account&coupon={account.coupon}'))
    await bot.edit_message_text("Аккаунты найдены, нажите кнопку ниже для открытия аккаунта",
                                message_id=cancel_message_id, reply_markup=keyboard.as_markup(),
                                chat_id=message.from_user.id)


@admin_router.callback_query(F.data.startswith(['log_key', 'log_user']))
async def input_cache(call: CallbackQuery, state: FSMContext):
    if call.data == 'log_key':
        await call.message.edit_text('<b>Введите ключ:</b>', reply_markup=CANCEL_KEYBOARD.as_markup())
        await state.set_state(StateWaitMessage.input_key_for_log)
    elif call.data == 'log_user':
        await call.message.edit_text('<b>Введите ID пользователя:</b>', reply_markup=CANCEL_KEYBOARD.as_markup())
        await state.set_state(StateWaitMessage.input_telegram_id)
    await state.update_data(cancel_message_id=call.message.message_id)


@admin_router.message(StateWaitMessage.input_key_for_log)
async def get_log_key(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    cancel_message_id = data['cancel_message_id']
    await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=cancel_message_id)
    key = message.text
    await message.delete()
    if not re.match(r'^[a-z0-9]{16}$', message.text):
        return await bot.edit_message_text(f'<b>Ключ: <code>{key}</code> отсутствует в базе</b>',
                                           chat_id=message.from_user.id, message_id=cancel_message_id)
    account_data = await account_repository.get_account_by_coupon(coupon=key)
    if not account_data:
        return await bot.edit_message_text(f'<b>Ключ: <code>{key}</code> отсутствует в базе</b>',
                                           chat_id=message.from_user.id, message_id=cancel_message_id)
    is_used = True if account_data.user_id is not None else False
    login_method = "Активация"
    tg_user_id = account_data.user_id
    try:
        tg_username = account_data.user.username
    except:
        tg_username = None
    phone_number = account_data.number
    date = account_data.creation_date
    await bot.edit_message_text(
        f'<b>Ключ: <code>{key}</code>\nИспользован ли ключ: <code><i>{is_used}</i></code>\nСпособ использования ключа: <i>{login_method}</i>\nID человека: <code>{tg_user_id}</code>\nЛогин человека: <code>{tg_username}</code>\nВнедренный в ключ номер: <code>{phone_number}</code>\nДата регистрации ключа: <i>{date}</i></b>',
        chat_id=message.from_user.id, message_id=cancel_message_id)


@admin_router.message(StateWaitMessage.input_telegram_id)
async def user_log(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=data['cancel_message_id'])
    await state.clear()
    if not message.text.isdigit():
        return await bot.edit_message_text(text='<b>Введите правильно Telegram Id</b>',
                                           chat_id=message.from_user.id,
                                           message_id=data['cancel_message_id'])
    tg_user_id = int(message.text)
    user_data = await user_repository.get_user(user_id=tg_user_id)
    if user_data is None:
        return await bot.edit_message_text(text='<b>Такой аккаунт отсутствует в базе</b>',
                                           chat_id=message.from_user.id,
                                           message_id=data['cancel_message_id'])
    purchases = await account_repository.get_accounts_by_user_id(
        user_id=tg_user_id,
        is_delete=True) + await account_repository.get_accounts_by_user_id(
        user_id=tg_user_id, is_delete=False)
    date = user_data.creation_date
    await message.answer(
        f'<b>ID человека: <code>{tg_user_id}</code>\n'
        f'Дата регистрации: <i>{date}</i>\n'
        f'Использовано ключей {len(purchases)}</b>')
    async with aiofiles.open(f'temp/{tg_user_id}.log', 'w+') as t:
        for log in os.listdir('logs'):
            async with aiofiles.open(f'logs/{log}', 'r') as f:
                async for line in f:
                    if str(tg_user_id) in line:
                        await t.write(f'{line}\n')
    await message.answer_document(document=f'temp/{tg_user_id}.log')
    os.remove(f'temp/{tg_user_id}.log')
