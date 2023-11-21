# -*- coding: utf-8 -*-
from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

MAIN_MENU = ReplyKeyboardBuilder()
MAIN_MENU.row(KeyboardButton(text='🔑 Ввести ключик'))
MAIN_MENU.row(KeyboardButton(text='ℹ️ Личный кабинет'))
MAIN_MENU.row(KeyboardButton(text='💬 Помощь'))

CANCEL_KEYBOARD = InlineKeyboardBuilder()
CANCEL_KEYBOARD.add(InlineKeyboardButton(text="Отмена", callback_data="cancel")).as_markup()
