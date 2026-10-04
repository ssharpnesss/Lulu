from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import Message

from app.config import Config
from app.filters.lulu import LuluFilter
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import Setting

from .keyboards.setting_keyboard import setting_menu

router = Router()

@router.message(LuluFilter(command=["настройки", "настр", "защита", "з", "н"]), IsChatAdmin())
async def cmd_set_protect_handler(
    message: Message,
    config: Config,
    lulu_args: dict[list],
):
    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return await message.answer("Lulu подсказывает:\nТакие команды используются только в чатах!") # можно будет брать где чел админ/владелец и открывать в лс

    args = lulu_args
    if len(args) != 2:

        await message.reply(
            text=f"Настройки чата «<b>{message.chat.title}</b>»",
            reply_markup=await setting_menu(message.from_user.id, message.chat.id))
        return

    protect, status_text = str(args[0]), str(args[1])
    protect = {"антиспам": "antispam"}.get(protect, protect)
    if protect not in {item["name"].casefold() for item in config.bot.protects}:
        return await message.answer("У Lulu нет такой защиты.")

    statuses = {"вкл": True, "включить": True, "выкл": False, "выключить": False}
    if status_text not in statuses:
        return await message.answer("Lulu не знает такой статус защиты.")

    status = statuses[status_text]
    await Setting.set_setting(message.chat.id, protect, "on" if status else "off")
    await message.answer(f"Я {'включила' if status else 'выключила'} {protect}")
