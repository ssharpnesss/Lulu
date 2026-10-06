import logging
from collections import deque
from time import monotonic

from aiogram import BaseMiddleware, Dispatcher
from aiogram.exceptions import TelegramAPIError
from database.models.setting import Setting

logger = logging.getLogger(__name__)


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self):
        self.messages = {}
        self.warnings = {}
        self.next_cleanup = 0.0
        self.expires = {}

    async def __call__(self, handler, message, data):
        if (
            message.chat.type not in {"group", "supergroup"}
            or message.from_user is None
            or message.sender_chat is not None
        ):
            return await handler(message, data)

        key = (message.chat.id, message.from_user.id)
        if not await Setting.is_enabled(message.chat.id, "antiflood"):
            self.messages.pop(key, None)
            self.warnings.pop(key, None)
            self.expires.pop(key, None)
            return await handler(message, data)

        parameters = await Setting.get_antiflood_parameters(message.chat.id)
        limit = parameters["limit"]
        interval = parameters["interval"]
        warning_interval = parameters["warning_interval"]
        now = monotonic()

        if now >= self.next_cleanup:
            self.messages = {
                key: times
                for key, times in self.messages.items()
                if self.expires.get(key, 0) > now
            }
            self.warnings = {
                key: timestamp
                for key, timestamp in self.warnings.items()
                if self.expires.get(key, 0) > now
            }
            self.expires = {key: expiry for key, expiry in self.expires.items() if expiry > now}
            self.next_cleanup = now + 60

        self.expires[key] = now + max(interval, warning_interval)
        times = self.messages.get(key)
        if times is None or times.maxlen != limit + 1:
            times = deque(times or (), maxlen=limit + 1)
            self.messages[key] = times

        while times and now - times[0] >= interval:
            times.popleft()

        times.append(now)

        if len(times) <= limit:
            return await handler(message, data)

        should_warn = (
            now - self.warnings.get(key, float("-inf"))
            >= warning_interval
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
