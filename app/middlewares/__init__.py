from aiogram import Dispatcher

def register_middlewares(dp: Dispatcher):
    from . import tracking
    tracking.register_middleware(dp=dp)