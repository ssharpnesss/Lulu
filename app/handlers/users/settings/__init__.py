from aiogram import Router

def get_setting_router():

    from .antispam import router as antispam_router
    from .welcome import router as welcome_router
    from .captcha import router as captcha_router
    from .captcha_image import router as captcha_image_router

    router = Router()
    router.include_router(antispam_router)
    router.include_router(captcha_router) # до welcome: каптча пропускает событие дальше
    router.include_router(captcha_image_router)
    router.include_router(welcome_router)

    return router