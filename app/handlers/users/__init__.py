from aiogram import Router

from app.handlers.users.start import router as start_router
from app.handlers.users.new_chat import router as new_chat_router
from app.handlers.users.commands import get_commands_router
from app.handlers.users.settings import get_setting_router

from app.handlers.users.settings.stat import router as stat_router 

router = Router()

def get_users_handlers():
    router.include_router(start_router)
    router.include_router(new_chat_router)
    router.include_router(get_commands_router())
    router.include_router(get_setting_router())
    router.include_router(stat_router) # ВСЕГДА ДОЛЖЕН БЫТЬ САМЫМ ПОСЛЕДНИМ



    return router
