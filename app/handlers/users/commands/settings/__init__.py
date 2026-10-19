from aiogram import Router

from app.filters.chat_type import IsGroup

def get_command_setting_router():

    from .setting import router as setting_router
    from .welcome import router as welcome_router
    from .parting import router as parting_router
    from .rules import router as rules_router
    from .commands import router as commands_router

    router = Router()
    router.message.filter(IsGroup)
    router.include_router(setting_router)
    router.include_router(welcome_router)
    router.include_router(parting_router)
    router.include_router(rules_router)
    router.include_router(commands_router)

    return router
