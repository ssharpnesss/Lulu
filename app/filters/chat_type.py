from aiogram import F
from aiogram.enums import ChatType

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}

IsGroup = F.chat.type.in_(GROUP_TYPES)
