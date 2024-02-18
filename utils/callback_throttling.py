import asyncio
import time
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery

from data.settings import CALLBACK_SPAM_TIMING
from loader import logger


class CallbackSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.storage = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        {'timestamp': 123001, 'spam_block': False}
        """

        user = f'user{event.from_user.id}'
        check_user = self.storage.get(user)
        if check_user:

            if check_user['spam_block']:
                return

            if time.time() - check_user['timestamp'] <= CALLBACK_SPAM_TIMING:
                self.storage[user]['timestamp'] = time.time()
                self.storage[user]['spam_block'] = True
                await event.answer(f'Обнаружена подозрительная активность.')
                logger.log('SPAM', user)
                await asyncio.sleep(CALLBACK_SPAM_TIMING)
                self.storage[user]['spam_block'] = False
                return

        self.storage[user] = {'timestamp': time.time(), 'spam_block': False}
        return await handler(event, data)
