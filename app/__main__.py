import asyncio
import logging
from app.config import parse_config
from app.args import parse_arguments

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers import get_handlers
from app.middlewares import register_middlewares
from database import init_database


async def main() -> None:
    init_database()
    args = parse_arguments()
    config = parse_config(args.config)

    bot = Bot(
        token=config.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_handlers())
    register_middlewares(dp)

    await bot.delete_webhook(True)
    await dp.start_polling(bot, config=config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
