import math

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import Accounts


class Paginator(object):
    def __init__(self, data: list[Accounts]):
        self.data = data

    async def generate_purchase_list_keyboard(self, page: int = 0):
        keyboard = InlineKeyboardBuilder()
        for number, item in enumerate(self.data[page * 4:page * 4 + 4]):
            coupon = item.coupon
            date = item.creation_date.strftime('%Y-%m-%d %H:%M:%S')
            keyboard.row(InlineKeyboardButton(text=coupon, callback_data=f'purchase_history|send_activation_date&date={date}'))
        keyboard.row(InlineKeyboardButton(text="⬅️", callback_data=f"purchase_history|page_back&page={page}"), InlineKeyboardButton(text=f"{page + 1}/{math.ceil(len(self.data) / 4)}", callback_data=f"purchase_history|page_now&page={page}"), InlineKeyboardButton(text="➡️", callback_data=f"purchase_history|page_next&page={page}"))
        keyboard.row(InlineKeyboardButton(text='🔙 Назад в личный кабинет', callback_data='return_to_personal_account'))
        return keyboard

    async def generate_accounts_list_keyboard(self, page: int = 0):
        keyboard = InlineKeyboardBuilder()
        for number, item in enumerate(self.data[page * 4:page * 4 + 4]):
            phone_number = item.number
            coupon = item.coupon
            keyboard.row(InlineKeyboardButton(text=f'{phone_number[:-4]}****', callback_data=f"get_account&coupon={coupon}"))
        keyboard.row(InlineKeyboardButton(text='Добавить личный аккаунт', callback_data=f'add_personal_account'))
        keyboard.row(InlineKeyboardButton(text="⬅️", callback_data=f"accounts_list|page_back&page={page}"), InlineKeyboardButton(text=f"{page + 1}/{math.ceil(len(self.data) / 4)}", callback_data=f"accounts_list|page_now&page={page}"), InlineKeyboardButton(text="➡️", callback_data=f"accounts_list|page_next&page={page}"))
        keyboard.row(InlineKeyboardButton(text='🔙 Назад в личный кабинет', callback_data='return_to_personal_account'))
        return keyboard
