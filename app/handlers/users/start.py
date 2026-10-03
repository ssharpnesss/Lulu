from aiogram import Router
from aiogram.filters.command import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Привет! Я Lulu — бот для модерации и управления чатом.")
