from aiogram import Router
from aiogram.types import Message

from app.filters.lulu import LuluFilter
from app.filters.setting import CommandEnabled
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import Setting

from app.utils.welcome import render_welcome

from .keyboards.setting_keyboard import get_only_setting_menu

router = Router(name="setting_parting")


@router.message(LuluFilter(command=["прощание"], is_equals=True), CommandEnabled("прощание"))
async def get_parting_chat_handler(message: Message):

    parting_text = await Setting.get_setting_value(message.chat.id, "parting")
    if not parting_text or parting_text == "off":
        return await message.reply(f"Прощание для чата «<b>{message.chat.title}</b>» отсутствует.")

    await message.reply(f"Прощание чата «<b>{message.chat.title}</b>»:\n\n<blockquote>{parting_text}</blockquote>")


@router.message(LuluFilter(command=["-прощание", "-пока"], is_equals=True), IsChatAdmin())
async def remove_parting_chat_handler(message: Message):

    await Setting.set_setting(message.chat.id, "parting", None)
    await message.reply(f"Прощание чата «<b>{message.chat.title}</b>» очищено.")


@router.message(LuluFilter(command=["+прощание", "+пока"]), IsChatAdmin())
async def update_parting_chat_handler(message: Message):

    lines = message.html_text.splitlines()
    parting_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

    if not parting_text:
        return await message.reply(
            text="Текст прощания необходимо указать с новой строки - либо используй кнопку ниже",
            reply_markup=await get_only_setting_menu(
                "parting",
                message.from_user.id,
                message.chat.id,
                button_text="Настроить [name]",
                button_emoji="5395444784611480792"
            )
        )

    try:
        render_welcome(parting_text, message.from_user, message.chat)
    except ValueError as error:
        return await message.reply(str(error))

    await Setting.set_setting(message.chat.id, "parting", parting_text)
    await message.reply(f"Прощание чата «<b>{message.chat.title}</b>» обновлено.")
