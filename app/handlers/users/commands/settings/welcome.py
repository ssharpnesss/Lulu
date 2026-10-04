from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import Message

from app.config import Config
from app.filters.lulu import LuluFilter
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import Setting

from app.utils.welcome import render_welcome

from .keyboards.setting_keyboard import get_only_setting_menu

router = Router(name="setting_welcome")


@router.message(LuluFilter(command=["скажи привет", "приветствуй"]))
async def say_welcome_handler(message: Message, config: Config):

    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return

    if not message.reply:
        return
    
    welcome_text = await Setting.get_setting_value(message.chat.id, "welcome")
    if not welcome_text:
        return await message.reply(f"Приветствие для чата «<b>{message.chat.title}</b>» отсутствует.")

    target = message.reply_to_message.from_user
    render_welcome_text = render_welcome(welcome_text, target)

    await message.reply_to_message.reply(render_welcome_text)
    

@router.message(LuluFilter(command=["приветствие"], is_equals=True))
async def get_welcome_chat_handler(message: Message):

    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return

    welcome_text = await Setting.get_setting_value(message.chat.id, "welcome")
    if not welcome_text:
        return await message.reply(f"Приветствие для чата «<b>{message.chat.title}</b>» отсутствует.")

    await message.reply(f"Приветствие чата «<b>{message.chat.title}</b>»:\n\n<blockquote>{welcome_text}</blockquote>")
    return


@router.message(LuluFilter(command=["-приветствие", "-привет"], is_equals=True), IsChatAdmin())
async def remove_welcome_chat_handler(message: Message):

    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return

    await Setting.set_setting(message.chat.id, "welcome", None)
    await message.reply(f"Приветствие чата «<b>{message.chat.title}</b>» очищено.")

@router.message(LuluFilter(command=["+приветствие", "+привет"]), IsChatAdmin())
async def update_welcome_chat_handler(message: Message, config: Config, lulu_args: dict[list]):

    welcome_text = message.html_text.splitlines()[1:] if len(message.html_text.splitlines()) > 1 else None

    if not welcome_text:
        return await message.reply(
            text=f"Укажи текст приветственного сообщения для чата «<b>{message.chat.title}</b>»",
            reply_markup=await get_only_setting_menu(
                "welcome",
                message.from_user.id, 
                message.chat.id,
                button_text="Настроить [name]",
                button_emoji="5395444784611480792"
            )
        )
    
    await Setting.set_setting(message.chat.id, "welcome", "\n".join(welcome_text))
    await message.reply(f"Приветствие чата «<b>{message.chat.title}</b>» обновлено.")
    
    