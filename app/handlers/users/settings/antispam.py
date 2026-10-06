import asyncio

from aiogram import Router, F
from aiogram.types import Message

from app.filters.setting import SettingEnable
from app.filters.is_chat_admin import IsBotPermission

from database.models.setting import Setting
from app.utils.predict import classify
from app.utils.text import clean_and_normalize_text
from app.config import Config

router = Router(name="antispam")

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text | F.caption, SettingEnable("antispam"), IsBotPermission("delete"))
async def cmd_antispam_detect_handler(message: Message, config: Config):

    text = message.text or message.caption
    if not text or not text.strip():
        return

    safe_text = clean_and_normalize_text(text)

    result = classify(safe_text)
    if result["label"] == "SPAM":
        if result["prob_spam"] >= config.bot.spam_threshold:
            msg = await message.reply("Lulu считает это сообщение спамом поэтому оно удаляется!")
            await asyncio.sleep(3)
            await message.delete()
            await msg.delete()
