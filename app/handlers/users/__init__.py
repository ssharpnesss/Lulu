from aiogram import Router

from app.handlers.users.start import router as start_router
from app.handlers.users.new_chat import router as new_chat_router
from app.handlers.users.protects.antispam import router as antispam_router
from app.handlers.users.commands import get_commands_handlers

router = Router()

def get_users_handlers():
    router.include_router(start_router)
    router.include_router(new_chat_router)
    router.include_router(get_commands_handlers())
    router.include_router(antispam_router)

    return router
