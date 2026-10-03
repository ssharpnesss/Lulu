from aiogram import Router

from app.handlers.users import get_users_handlers

router = Router()

def get_handlers():
    router.include_router(get_users_handlers())

    return router
