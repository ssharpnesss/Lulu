from aiogram import Router

def get_command_setting_router():

    from .setting import router as setting_router
    from .welcome import router as welcome_router

    router = Router()
    router.include_router(setting_router)
    router.include_router(welcome_router)

    return router
