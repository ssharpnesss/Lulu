from database.models.user import User
from database.models.chat import Chat, ChatMember
from database.models.statistic import MessageStatistic

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import Message, CallbackQuery, TelegramObject

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
            await Chat.update_chat(event.chat)
            await ChatMember.update_member(event.chat.id, event.from_user.id, "member")

        if event.from_user is not None and not event.from_user.is_bot and event.sender_chat is None:
            await User.update_user(event.from_user)

        await MessageStatistic.add_message(event)

        return await handler(event, data)

def register_middleware(dp: Dispatcher):
    track_middleware = TrackMiddleware()
    dp.message.middleware(track_middleware)
