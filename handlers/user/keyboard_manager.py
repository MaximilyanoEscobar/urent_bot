import asyncio
import random

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import any_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from data.keyboards import MAIN_MENU
from data.settings import ADMIN_LIST, STICKER_ID
from db.repository import account_repository
from db.repository import user_repository
from loader import StateWaitMessage

keyboard_router = Router(name='keyboard_router')


@keyboard_router.message(Command('start'), any_state)
async def get_text_messages(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    tg_user_id = message.from_user.id
    tg_username = message.from_user.username
    user_data = await user_repository.get_user(user_id=tg_user_id)

    if user_data is None:
        await user_repository.add_user(user_id=tg_user_id, username=tg_username)
        try:
            await asyncio.gather(*(asyncio.create_task(bot.send_message(
                chat_id=admin_id,
                text=f"<b>👤 Зарегистрирован новый пользователь:\n"
                    f"ID: <code>{tg_user_id}</code>\n"
                    f"Username: <a href='{message.from_user.url}'>{message.from_user.full_name}</a></b>"))
                for admin_id in ADMIN_LIST))
        except:
            pass
        logger.log("JOIN", f"{tg_user_id} | @{tg_username}")

    await message.answer_sticker(random.choice(STICKER_ID))
    await message.answer(
        f"<b>Добро пожаловать, {message.from_user.full_name}, спасибо что заглянул ко мне ❤\n"
        f"Я - Urent 5.0,\n"
        f"И я хочу Вам помочь прокатиться с ветерком на самокате 🥰\n"
        "<i><a href='https://telegra.ph/Instrukciya-po-ispolzovaniyu-telegramm-bota-UrentPro-06-26'>Инструкция для новых пользователей</a></i></b>",
        reply_markup=MAIN_MENU.as_markup(resize_keyboard=True))


@keyboard_router.message(F.text=='🔑 Ввести ключик')
async def enter_key(message: Message, state: FSMContext):
    await message.reply('<b>Напишите мне пожалуйста ключ, который Вы приобрели в боте 😘</b>')
    await state.set_state(StateWaitMessage.input_key)


@keyboard_router.message(F.text=='💬 Помощь')
@keyboard_router.message(Command('help'))
async def help_answer(message: Message):
    await message.reply(
        '<b><a href="https://telegra.ph/Instrukciya-po-ispolzovaniyu-telegramm-bota-UrentPro-06-26">Инструкция для новых пользователей</a>\n'
        'Тех. поддержка: @SHADOW1CH</b>')


@keyboard_router.message(StateWaitMessage.input_key)
async def input_key(message: Message, state: FSMContext):
    await state.clear()
    coupon = message.text
    tg_user_id = message.from_user.id
    account_data = await account_repository.get_account_by_coupon(coupon=coupon)
    if account_data is not None and account_data.user_id is None:
        await account_repository.update_account_user_id(account_data.id, user_id=tg_user_id)
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text='Перейти к аккаунту',
                                          callback_data=f'get_account&coupon={coupon}'))
        await message.answer('<b>✅ Ключ подошёл 😉\n'
                             '📝 Аккаунт успешно загружен в личный кабинет!</b>',
                             reply_markup=keyboard.as_markup())
        logger.log("USE-KEY", f"{tg_user_id} | {coupon}")
    else:
        await message.answer(f"<b>❌ Ключ не подходит 😥</b>")


@keyboard_router.callback_query(F.data == 'return_to_personal_account')
@keyboard_router.message(F.text == 'ℹ️ Личный кабинет')
async def personal_area(event: CallbackQuery | Message):

    personal_area_menu = InlineKeyboardBuilder()
    personal_area_menu.row(InlineKeyboardButton(text="История активаций", callback_data="purchase_history|send_initial_menu"))
    personal_area_menu.row(InlineKeyboardButton(text="Мои аккаунты", callback_data="accounts_list|send_initial_menu"))

    tg_user_id = event.from_user.id
    accounts_deleted = await account_repository.get_accounts_by_user_id(user_id=tg_user_id, is_delete=True)
    accounts_not_deleted = await account_repository.get_accounts_by_user_id(user_id=tg_user_id)
    number_of_purchases = len(accounts_deleted) + len(accounts_not_deleted)
    user_data = await user_repository.get_user(user_id=tg_user_id)
    registration_date = user_data.creation_date.strftime('%Y-%m-%d %H:%M:%S')
    message_text = f'<b>💜 Пользователь: @{event.from_user.username}\n' \
                   f'🔑 ID: <code>{tg_user_id}</code>\n' \
                   f'💸 Количество покупок: {number_of_purchases}\n' \
                   f'📋 Дата регистрации: {registration_date}</b>'
    if type(event) == CallbackQuery:
        try:
            await event.message.edit_text(message_text, reply_markup=personal_area_menu.as_markup())
        except Exception:
            await event.message.answer(message_text, reply_markup=personal_area_menu.as_markup())
    else:
        try:
            await event.edit_text(message_text, reply_markup=personal_area_menu.as_markup())
        except Exception:
            await event.answer(message_text, reply_markup=personal_area_menu.as_markup())


@keyboard_router.message()
async def any_messages(message: Message):
    await message.reply(f"Я вас не понимаю 😥\n"
                        f"Напишите <b>/start</b> или <b>/help</b>")