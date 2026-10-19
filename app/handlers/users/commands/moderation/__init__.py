from aiogram import Router

from app.filters.chat_type import IsGroup

def get_moderation_router():

    from .mute import router as mute_router
    from .ban import router as ban_router
    from .kick import router as kick_router
    from .warn import router as warn_router

    router = Router(name="moderation")
    router.message.filter(IsGroup)
    router.include_router(mute_router)
    router.include_router(ban_router)
    router.include_router(kick_router)
    router.include_router(warn_router)

    return router
