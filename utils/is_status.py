import traceback

from aiogram.client import bot

from data.settings import ADMIN_LIST
from loader import bots_list


def is_admin(func):
    async def wrapper(*args, **kwargs):
        try:
            if args[0].from_user.id in ADMIN_LIST:
                return await func(*args)
        except Exception:
            print(traceback.format_exc())

    return wrapper
