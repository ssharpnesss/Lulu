from aiogram import Router

def get_setting_router():

    from .antispam import router as antispam_router
    from .welcome import router as welcome_router

    router = Router()
    router.include_router(antispam_router)
    router.include_router(welcome_router)

    return router