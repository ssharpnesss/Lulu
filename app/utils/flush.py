import asyncio
import logging

from peewee import EXCLUDED, chunked

from app.utils.buffer import buffer
from database.loader import db
from database.models.chat import Chat, ChatMember
from database.models.statistic import MessageStatistic
from database.models.user import User

BATCH = 50  # лимит переменных в SQLite

_lock = asyncio.Lock()


def _write(data: tuple) -> None:
    messages, users, chats, members = data

    with db.atomic():
        for batch in chunked(users.values(), BATCH):
            User.insert_many(batch).on_conflict(
                conflict_target=[User.user_id],
                update={
                    User.first_name: EXCLUDED.first_name,
                    User.last_name: EXCLUDED.last_name,
                    User.username: EXCLUDED.username,
                    User.updated_at: EXCLUDED.updated_at,
                },
            ).execute()

        for batch in chunked(chats.values(), BATCH):
            Chat.insert_many(batch).on_conflict(
                conflict_target=[Chat.chat_id],
                update={
                    Chat.chat_name: EXCLUDED.chat_name,
                    Chat.chat_type: EXCLUDED.chat_type,
                    Chat.username: EXCLUDED.username,
                    Chat.updated_at: EXCLUDED.updated_at,
                },
            ).execute()

        rows = [{"chat_id": c, "user_id": u, "status": "member"} for c, u in members]
        for batch in chunked(rows, BATCH):
            ChatMember.insert_many(batch).on_conflict_ignore().execute()

        for batch in chunked(messages, BATCH):
            MessageStatistic.insert_many(batch).execute()


async def flush() -> None:
    async with _lock:
        data = buffer.swap()
        if not any(data):
            return
        try:
            await asyncio.to_thread(_write, data)
        except Exception as e:
            logging.exception(f"Не удалось сбросить буфер в БД, возвращаю обратно\n{e}")
            buffer.restore(data)
