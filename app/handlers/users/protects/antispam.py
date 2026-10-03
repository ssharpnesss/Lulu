import asyncio

from aiogram import Router, F
from aiogram.types import Message

from database.models.protects import Protects
from app.utils.predict import predict

router = Router(name="antispam")


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text | F.caption)
async def cmd_antispam_detect_handler(message: Message):
    if message.from_user is not None and message.from_user.is_bot:
        return
    if not await Protects.is_enabled(message.chat.id, "antispam"):
        return

    text = message.text or message.caption
    if not text or not text.strip():
        return

    result = predict(text)
    print(f"{text} - {result}")
    if result == 1:
        await message.reply("Lulu считает это сообщение спамом поэтому оно удаляется!")
        await asyncio.sleep(3)
        await message.delete()
    