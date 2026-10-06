from aiogram.filters import BaseFilter
from aiogram.types import Message

from database.models.setting import Setting

class SettingEnable(BaseFilter):
    def __init__(self, protect):
        self.protect = protect

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None: return False
        if message.from_user.is_bot: return False

        return await Setting.is_enabled(message.chat.id, self.protect)
        