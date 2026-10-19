from aiogram import Router
from aiogram.types import Message

from app.filters.lulu import LuluFilter
from app.filters.setting import CommandEnabled
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import Setting

from app.utils.emoji import get_emoji

router = Router(name="setting_commands")

TOGGLEABLE_COMMANDS = {
    "правила": "правила",
    "приветствие": "приветствие",
    "прощание": "прощание",
    "стата": "стата",
    "пошли его нахуй": "пошли его нахуй"
}


@router.message(LuluFilter(command=["команды"], is_equals=True), IsChatAdmin())
async def list_commands_handler(message: Message):

    disabled = await Setting.get_disabled_commands(message.chat.id)
    lines = [f"{get_emoji('off_status') if key in disabled else get_emoji('on_status')} {name}" for key, name in TOGGLEABLE_COMMANDS.items()]
    await message.reply(
        "Команды чата:\n" + "\n".join(lines)
        + "\n\n<code>лу выкл кмнд [название]</code>\n<code>лу вкл кмнд [название]</code>"
    )


@router.message(LuluFilter(command=["выключить команду", "включить команду", "выкл кмнд", "вкл кмнд"]), IsChatAdmin())
async def toggle_command_handler(message: Message, lulu_args: list[str]):

    disable = bool({"выключить", "выкл"} & set(message.text.casefold().split()[:2]))
    key = " ".join(lulu_args).casefold().lstrip("+-")
    if key not in TOGGLEABLE_COMMANDS:
        return await message.reply("Такой команды нет. Список: <code>лу команды</code>")

    await Setting.set_command_disabled(message.chat.id, key, disable)
    await message.reply(f"Команда «<b>{key}</b>» {'отключена' if disable else 'включена'}.")

@router.message(LuluFilter(command=["пошли его нахуй"], is_equals=True), CommandEnabled("пошли его нахуй"))
async def say_fuck_handler(message: Message, lulu_args: dict[list]):

    reply_id = None

    if message.reply_to_message: reply_id = message.reply_to_message.message_id

    if reply_id is None:
        reply_id = message.message_id - 1

    text = (
        "Меня попросили тебе передать\n"
        "<tg-spoiler>ПОШЕЛ НАХУЙ</tg-spoiler>"
    )
    await message.answer(
        text=text,
        reply_to_message_id=reply_id
    )
