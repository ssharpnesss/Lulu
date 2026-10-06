from aiogram import Dispatcher

def register_middlewares(dp: Dispatcher):
    from . import tracking
    from . import antiflood

    tracking.register_middleware(dp=dp)
    antiflood.register_middleware(dp=dp)