from aiogram import Router
from aiogram.types import Message
from aiogram.filters.command import Command

from app.config import Config

from database.models.protects import Protects

router = Router()


@router.message(Command("protect"))
async def cmd_set_protect_handler(message: Message, config: Config):
    # /protect [name] [status]
    args = message.text.split()
    chat = message.chat

    if chat.type == "private":
        return await message.answer("Lulu подсказывает:\nТакие команды используются только в чатах!")
    else:
        if len(args) >= 3:
            protect = args[1].lower()
            status = str(args[2])
    
            if protect not in {item["name"].lower() for item in config.bot.protects}:
                return await message.answer("У Lulu нет такой защиты.")
    
            if status.lower() in ["вкл", "включить"]:
                status = True
            else:
                if status.lower() in ["выкл", "выключить"]:
                    status = False
                else:
                    return await message.answer("Lulu не знает такой статус защиты.")
    
            await Protects.set_protection(chat.id, protect, status)
            await message.answer(f"Я {'включила' if status else 'выключила'} {protect}")
        else:
            return await message.answer("Lulu подсказывает правильную команду:\n/protect [имя] [статус]")
