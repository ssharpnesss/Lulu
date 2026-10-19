from aiogram.fsm.state import State, StatesGroup

class ProtectionInput(StatesGroup):
    value = State()

class CaptchaPackInput(StatesGroup):
    waiting = State()
