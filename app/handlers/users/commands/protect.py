from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.config import Config
from app.filters.lulu import LuluFilter
from app.filters.is_chat_admin import IsChatAdmin
from database.models.protects import Protects

router = Router()


@router.message(LuluFilter(command=["настройки", "настр", "защита"]), IsChatAdmin())
async def cmd_set_protect_handler(
    message: Message,
    config: Config,
    lulu_args: dict[list],
):
    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return await message.answer("Lulu подсказывает:\nТакие команды используются только в чатах!")

    args = lulu_args
    if len(args) != 2:
        return await message.answer(
            "Lulu подсказывает правильную команду:\n"
            "Лулу защита антиспам вкл"
        )

    protect, status_text = str(args[0]), str(args[1])
    protect = {"антиспам": "antispam"}.get(protect, protect)
    if protect not in {item["name"].casefold() for item in config.bot.protects}:
        return await message.answer("У Lulu нет такой защиты.")

    statuses = {"вкл": True, "включить": True, "выкл": False, "выключить": False}
    if status_text not in statuses:
        return await message.answer("Lulu не знает такой статус защиты.")

    status = statuses[status_text]
    await Protects.set_protection(message.chat.id, protect, status)
    await message.answer(f"Я {'включила' if status else 'выключила'} {protect}")
