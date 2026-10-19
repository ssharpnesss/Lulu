from aiogram import F, Router
from aiogram.filters.command import CommandObject, CommandStart
from aiogram.types import Message

from app.handlers.users.settings.captcha_image import open_image_captcha
from app.handlers.users.settings.keyboards.captcha_image_keyboard import DEEP_LINK_PREFIX

router = Router()

@router.message(
    CommandStart(deep_link=True, magic=F.args.regexp(rf"^{DEEP_LINK_PREFIX}-?\d+$")),
    F.chat.type == "private",
)
async def start_captcha(message: Message, command: CommandObject) -> None:
    await open_image_captcha(message, int(command.args.removeprefix(DEEP_LINK_PREFIX)))

@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Привет! Я Lulu — бот для модерации и управления чатом.")
