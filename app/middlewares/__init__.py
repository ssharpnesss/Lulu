from aiogram import Dispatcher

def register_middlewares(dp: Dispatcher):
    from . import tracking
    from . import antiflood
    from . import antiraid

    tracking.register_middleware(dp=dp)
    antiflood.register_middleware(dp=dp)
    antiraid.register_middleware(dp=dp)