import asyncio
import logging
import os
from collections import deque
from time import monotonic

from aiogram import BaseMiddleware, Bot, Dispatcher, Router
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit=5, interval=1.5, warning_interval=5):
        self.limit = limit
        self.interval = interval
        self.warning_interval = warning_interval

        self.messages = {}
        self.warnings = {}
        self.next_cleanup = 0.0

    async def __call__(self, handler, message, data):
        if (
            message.chat.type not in {"group", "supergroup"}
            or message.from_user is None
            or message.sender_chat is not None
        ):
            return await handler(message, data)

        now = monotonic()
        limit = self.limit 
        interval = self.interval
        work_status = True

        if now >= self.next_cleanup:
            self.messages = {
                key: times
                for key, times in self.messages.items()
                if times and now - times[-1] < self.interval
            }
            self.warnings = {
                key: timestamp
                for key, timestamp in self.warnings.items()
                if now - timestamp < self.warning_interval
            }
            self.next_cleanup = now + 60

        key = (message.chat.id, message.from_user.id)
        times = self.messages.setdefault(
            key, deque(maxlen=self.limit + 1)
        )

        while times and now - times[0] >= self.interval:
            times.popleft()

        times.append(now)

        if len(times) <= self.limit:
            return await handler(message, data)

        should_warn = (
            now - self.warnings.get(key, float("-inf"))
            >= self.warning_interval
        )

        if should_warn:
            self.warnings[key] = now

        try:
            await message.delete()
        except TelegramAPIError:
            logger.exception(
                "Не удалось удалить сообщение %s в чате %s",
                message.message_id,
                message.chat.id,
            )
            return

        if should_warn:
            try:
                
                await message.answer(
                    f"⚠️ {message.from_user.full_name}, не так быстро чучело\n",
                )
            except TelegramAPIError:
                logger.exception("Не удалось отправить предупреждение")

        return

def register_middleware(dp: Dispatcher):
    antiflood = AntiFloodMiddleware()
    dp.message.middleware(antiflood)
