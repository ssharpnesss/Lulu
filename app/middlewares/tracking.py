from database.models.user import User
from database.models.chats import Chats

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
            await Chats.update_chat(event.chat)

        if event.from_user is not None and not event.from_user.is_bot and event.sender_chat is None:
            await User.update_user(event.from_user)

        return await handler(event, data)

def register_middleware(dp: Dispatcher):
    track_middleware = TrackMiddleware()
    dp.message.outer_middleware(track_middleware)
