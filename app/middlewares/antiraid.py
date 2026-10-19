import asyncio
import logging
from collections import deque
from time import monotonic

from aiogram import BaseMiddleware, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberUpdated
from database.models.setting import Setting

from app.utils.emoji import get_emoji

logger = logging.getLogger(__name__)

JOIN_LIMIT = 5        # сколько входов
JOIN_INTERVAL = 10    # за сколько секунд считаются рейдом
RAID_DURATION = 60    # сколько секунд после срабатывания кикаем всех новых


class Raid:
    def __init__(self, until: float):
        self.until = until
        self.kicked = 0


def is_join(event: ChatMemberUpdated) -> bool:
    old, new = event.old_chat_member, event.new_chat_member
    was_in = old.status in {"member", "administrator", "creator"} or (
        old.status == "restricted" and getattr(old, "is_member", False)
    )
    is_in = new.status == "member" or (
        new.status == "restricted" and getattr(new, "is_member", False)
    )
    return not was_in and is_in


class AntiRaidMiddleware(BaseMiddleware):
    def __init__(self):
        self.joins: dict[int, deque] = {}
        self.raids: dict[int, Raid] = {}
        self.tasks: set[asyncio.Task] = set()

    async def kick(self, event: ChatMemberUpdated, user_id: int) -> bool:
        try:
            await event.bot.ban_chat_member(event.chat.id, user_id)
            await event.bot.unban_chat_member(event.chat.id, user_id, only_if_banned=True)
        except TelegramAPIError:
            logger.exception("Анти-рейд: не удалось кикнуть %s в чате %s", user_id, event.chat.id)
            return False
        return True

    async def report(self, event: ChatMemberUpdated, raid: Raid):
        await asyncio.sleep(max(raid.until - monotonic(), 0))
        chat_id = event.chat.id
        if self.raids.get(chat_id) is raid:
            del self.raids[chat_id]
        try:
            await event.bot.send_message(
                chat_id,
                f"{get_emoji('protect')} <b>Сработал анти-рейд.</b>\nКикнуто участников: <b>{raid.kicked}</b>",
            )
        except TelegramAPIError:
            logger.exception("Анти-рейд: не удалось отправить отчёт в чате %s", chat_id)

    async def __call__(self, handler, event: ChatMemberUpdated, data):
        if event.chat.type not in {"group", "supergroup"} or not is_join(event):
            return await handler(event, data)

        chat_id = event.chat.id
        if not await Setting.is_enabled(chat_id, "antiraid"):
            self.joins.pop(chat_id, None)
            self.raids.pop(chat_id, None)
            return await handler(event, data)

        user = event.new_chat_member.user
        if user.is_bot and event.new_chat_member.user.id == event.bot.id:
            return await handler(event, data)

        now = monotonic()
        raid = self.raids.get(chat_id)
        if raid is not None and now < raid.until:
            if await self.kick(event, user.id):
                raid.kicked += 1
            return

        joins = self.joins.setdefault(chat_id, deque())
        while joins and now - joins[0][0] >= JOIN_INTERVAL:
            joins.popleft()
        joins.append((now, user.id))

        if len(joins) <= JOIN_LIMIT:
            return await handler(event, data)

        raid = Raid(until=now + RAID_DURATION)
        self.raids[chat_id] = raid
        suspects = [user_id for _, user_id in joins]
        joins.clear()
        for user_id in suspects:
            if await self.kick(event, user_id):
                raid.kicked += 1

        task = asyncio.create_task(self.report(event, raid))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


def register_middleware(dp: Dispatcher):
    dp.chat_member.outer_middleware(AntiRaidMiddleware())
