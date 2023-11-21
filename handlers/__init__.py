
from handlers.admin.admin_panel import admin_router
from handlers.user.keyboard_manager import keyboard_router
from handlers.user.profile.profile_menu import profile_router
from handlers.user.account.account_manager import account_router
from loader import *


def register_user_commands(dp: Dispatcher) -> None:
    dp.include_router(profile_router)
    dp.include_router(account_router)
    dp.include_router(admin_router)
    dp.include_router(keyboard_router)



register_user_handlers = register_user_commands
