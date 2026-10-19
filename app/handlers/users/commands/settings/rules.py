from aiogram import Router
from aiogram.types import Message

from app.filters.lulu import LuluFilter
from app.filters.setting import CommandEnabled
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import Setting

router = Router(name="setting_rules")


@router.message(LuluFilter(command=["правила"], is_equals=True), CommandEnabled("правила"))
async def get_rules_chat_handler(message: Message):

    rules_text = await Setting.get_setting_value(message.chat.id, "rules")
    if not rules_text:
        return await message.reply(f"Правила для чата «<b>{message.chat.title}</b>» отсутствуют.")

    await message.reply(f"Правила чата «<b>{message.chat.title}</b>»:\n\n{rules_text}")


@router.message(LuluFilter(command=["-правила"], is_equals=True), IsChatAdmin())
async def remove_rules_chat_handler(message: Message):

    await Setting.set_setting(message.chat.id, "rules", None)
    await message.reply(f"Правила чата «<b>{message.chat.title}</b>» очищены.")


@router.message(LuluFilter(command=["+правила"]), IsChatAdmin())
async def update_rules_chat_handler(message: Message):

    lines = message.html_text.splitlines()
    rules_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

    if not rules_text:
        return await message.reply("Текст правил необходимо указать с новой строки.")

    await Setting.set_setting(message.chat.id, "rules", rules_text)
    await message.reply(f"Правила чата «<b>{message.chat.title}</b>» обновлены.")
