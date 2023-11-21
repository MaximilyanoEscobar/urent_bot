import traceback
from aiogram.types import BotCommand


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            BotCommand('start', '📃 Запуск бота'),
            BotCommand('🔑 Ввести ключик', '🔑 Ввести ключик'),
            BotCommand('ℹ️ Личный кабинет','ℹ️ Личный кабинет')
        ]
    )
