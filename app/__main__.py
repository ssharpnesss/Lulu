import asyncio
import logging
from app.config import parse_config
from app.args import parse_arguments

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.handlers import get_handlers
from app.middlewares import register_middlewares
from app.utils.flush import flush
from database import init_database


async def main() -> None:
    await init_database()
    args = parse_arguments()
    config = parse_config(args.config)

    bot = Bot(
        token=config.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_handlers())
    register_middlewares(dp)

    await bot.delete_webhook(drop_pending_updates=True)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(flush, "interval", seconds=30, max_instances=1, coalesce=True)
    scheduler.start()

    try:
        await dp.start_polling(bot, config=config)
    finally:
        scheduler.shutdown(wait=False)
        await flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
