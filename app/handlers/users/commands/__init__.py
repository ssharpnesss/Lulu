from aiogram import Router

def get_commands_router():

    from .settings import get_command_setting_router
    from .stats import router as stats_router
    from .moderation import get_moderation_router

    router = Router()
    router.include_router(get_command_setting_router())
    router.include_router(stats_router)
    router.include_router(get_moderation_router())

    return router