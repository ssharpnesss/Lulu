from aiogram import Router

from app.handlers.users.commands.protect import router as protect_router

router = Router()

def get_commands_handlers():
    router.include_router(protect_router)

    return router
