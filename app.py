# -*- coding: utf-8 -*-
import asyncio
import traceback
import datetime

import aiohttp.client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Style, Fore
from api.urent import UrentAPI
from handlers import register_user_commands
from loader import logger, bots_list
from utils.callback_throttling import CallbackSpamMiddleware
from utils.message_throttling import MessageSpamMiddleware
from db.repository import rides_repository
from db.repository import user_repository
from db.repository import account_repository


async def on_startup(dp):
    register_user_commands(dp)
    for bot in bots_list:
        await bot.delete_webhook(drop_pending_updates=True)
        bot_info = await bot.get_me()
        print(f"{Style.BRIGHT}{Fore.CYAN}https://t.me/{bot_info.username} запущен успешно!", Style.RESET_ALL)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(func=check_rides, trigger="interval", seconds=5)
    scheduler.add_job(func=remove_cards, trigger="cron", hour=6)
    scheduler.start()


async def remove_cards():
    users = await user_repository.select_all_users()
    async with aiohttp.ClientSession() as session:
        for user in users:
            tg_user_id = user.user_id
            accounts = await account_repository.get_accounts_by_user_id(tg_user_id)
            for account in accounts:
                refresh_token = account.refresh_token
                access_token = account.access_token
                phone_number = account.number
                urent_api = UrentAPI(session=session, refresh_token=refresh_token, access_token=access_token,
                                     phone_number=phone_number)
                credit_card_data: dict | bool = await urent_api.check_card_availability()
                if type(credit_card_data) is bool:
                    continue
                entries = bool(len(credit_card_data['entries']))
                active_urent_travel_check_json: dict = await urent_api.get_active_travel()
                activities = bool(len(active_urent_travel_check_json['activities']))
                if not entries:
                    continue
                elif not activities:
                    data_cards: list[dict] = credit_card_data["entries"]
                    cards_id = [data_card['id'] for data_card in data_cards]
                    await asyncio.gather(*map(urent_api.remove_card, cards_id))
                    logger.log("UNLINK-CARDS", f'{tg_user_id} | {phone_number}')
                    continue
                for bot in bots_list:
                    try:
                        await bot.send_message(chat_id=tg_user_id,
                                               text=f'<b>Не удалось отвязать автоматически карту от аккаунта <code>{phone_number[:-4]}****</code>!\n'
                                                    f'Как сможете отвязать карту - <u>отвяжите</u>, чтобы не возникло непредвиденных ситуаций с вашими средствами!</b>')
                    finally:
                        pass


async def check_rides():
    rides = await rides_repository.get_all_rides_not_finished()
    async with aiohttp.ClientSession() as session:
        for ride in rides:
            for bot in bots_list:
                if ride.bot_id != (await bot.get_me()).id:
                    continue
                break
            else:
                continue
            refresh_token = ride.account.refresh_token
            access_token = ride.account.access_token
            phone_number = ride.account.number
            tg_user_id = ride.account.user_id
            points = ride.account.points
            start_ride_time = ride.creation_date
            payment_field = ride.payment_field
            cost = payment_field['cost']
            activation_cost = 0 if payment_field['activation_cost'] == "" else payment_field['activation_cost']
            max_time = int((points - activation_cost) // cost)
            if not datetime.datetime.now() >= start_ride_time + datetime.timedelta(minutes=max_time):
                continue
            urent_api = UrentAPI(session, refresh_token, phone_number, access_token)
            active_travel_check_json: dict | bool = await urent_api.get_active_travel()
            if type(active_travel_check_json) is bool:
                await rides_repository.update_finish_ride(ride.id, finish_time=datetime.datetime.now())
                continue
            if not bool(len(active_travel_check_json['activities'])):
                await rides_repository.update_finish_ride(ride.id, finish_time=datetime.datetime.now())
                continue
            scooter_id = active_travel_check_json['activities'][0]['bikeIdentifier']
            response_json: dict | bool = await urent_api.stop_drive(scooter_id=scooter_id)
            if response_json['errors']:
                error = response_json['errors'][0]['value'][0]
                await bot.send_message(chat_id=tg_user_id,
                                       text=f'<b>Ошибка при автоматическом завершении самоката: <i>{error}</i>\n'
                                            f'Номер телефона: <code>{phone_number}</code></b>')
                continue
            logger.log("END-UR-RIDE", f'{tg_user_id} | {phone_number}')
            await rides_repository.update_finish_ride(ride.id, finish_time=datetime.datetime.now())
            await bot.send_message(chat_id=tg_user_id, text='<b>Поездка была автоматически завершена!\n'
                                                            f'Номер телефона: <code>{phone_number[:-4]}****</code></b>')


async def main(dp) -> None:
    await on_startup(dp)
    try:
        dp.message.middleware.register(MessageSpamMiddleware())
        dp.callback_query.middleware.register(CallbackSpamMiddleware())
        await dp.start_polling(*bots_list)
    except Exception:
        print(traceback.format_exc())


if __name__ == '__main__':
    from loader import dp

    asyncio.get_event_loop().run_until_complete(main(dp))
