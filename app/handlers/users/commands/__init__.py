from aiogram import Router

def get_commands_router():

    from .settings import get_command_setting_router
    from .stats import router as stats_router

    router = Router()
    router.include_router(get_command_setting_router())
    router.include_router(stats_router)

    return router