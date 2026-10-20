from database.models.user import User
from database.models.chat import Chat, ChatMember
from database.models.statistic import MessageStatistic

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import Message, CallbackQuery, TelegramObject
from app.utils.buffer import buffer
from app.utils.time import get_now
from app.utils.text import escape_html

class TrackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
    
        if not isinstance(event, Message):
            return await handler(event, data)

        if event.chat.type != "private":
            buffer.chats[event.chat.id] = {
                "chat_id": event.chat.id,
                "chat_name": event.chat.title or event.chat.full_name or str(event.chat.id),
                "chat_type": event.chat.type,
                "username": event.chat.username.lower() if event.chat.username else None,
                "updated_at": get_now(),
            }
            if event.from_user and not event.from_user.is_bot:
                buffer.members.add((event.chat.id, event.from_user.id))

        if event.from_user is not None and not event.from_user.is_bot and event.sender_chat is None:
            user = event.from_user
            db_user = await User.get_user(user.id)
            is_pm = event.chat.type == "private"
            if db_user and db_user.pm: is_pm = True

            buffer.users[user.id] = {
                "user_id": user.id,
                "first_name": escape_html(user.first_name),
                "last_name": escape_html(user.last_name) if user.last_name else None,
                "username": user.username.lower() if user.username else None,
                "pm": is_pm,
                "updated_at": get_now(),
            }

        row = MessageStatistic.add_message(event)
        if row:
            buffer.messages.append(row)

        return await handler(event, data)

def register_middleware(dp: Dispatcher):
    track_middleware = TrackMiddleware()
    dp.message.middleware(track_middleware)
