from aiogram.fsm.state import State, StatesGroup

class ProtectionInput(StatesGroup):
    value = State()