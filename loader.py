import datetime
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from data.settings import BOTS_TOKENS


class StateWaitMessage(StatesGroup):
    input_key = State()
    input_scooter = State()
    input_card = State()
    input_key_for_log = State()
    input_telegram_id = State()
    input_count_accounts = State()
    input_coupon_account_for_log = State()
    input_params_account_for_refresh = State()
    input_promo_codes = State()
    input_promo_code = State()
    input_phone_number = State()
    input_sms_code = State()
    input_coupon_to_refresh = State()


bots_list = [Bot(token=BOT_TOKEN, parse_mode='html') for BOT_TOKEN in BOTS_TOKENS]
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

logger.add(f"logs/{datetime.date.today()}.log", format="{time:DD-MMM-YYYY HH:mm:ss} | {level:^25} | {message}",
           enqueue=True, rotation="00:00")

logger.level("JOIN", no=60, color="<green>")

logger.level("SPAM", no=60, color="<red>")
logger.level("TOKEN IS EXPIRED", no=60, color="<red>")
logger.level("LINK-CARD-DENY", no=60, color="<red>")
logger.level("DELETE-ACCOUNT", no=60, color="<red>")

logger.level("USE-KEY", no=60, color="<blue>")
logger.level("START-UR-RIDE", no=60, color="<blue>")
logger.level("END-UR-RIDE", no=60, color="<blue>")
logger.level("PAUSE-UR-RIDE", no=60, color="<blue>")
logger.level("RESUME-UR-RIDE", no=60, color="<blue>")
logger.level("GET-COST-UR-RIDE", no=60, color="<blue>")

logger.level("LINK-CARD", no=60, color="<yellow>")
logger.level("UNLINK-CARDS", no=60, color="<yellow>")
