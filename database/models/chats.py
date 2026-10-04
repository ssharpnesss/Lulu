from peewee import BigIntegerField, BooleanField, CharField, DateTimeField, TextField

from database.loader import BaseModel

from datetime import datetime
from aiogram import types

class Chats(BaseModel):
    chat_id = BigIntegerField(unique=True)
    owner_id = BigIntegerField(null=True)
    added_by_id = BigIntegerField(null=True)
    chat_name = CharField(255)
    chat_type = CharField(default="group")
    username = CharField(null=True)
    is_deleted = BooleanField(default=False)
    welcome_template = TextField(null=True)

    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    @classmethod
    async def get_chat(cls, ident: str | int):
        if str(ident).lstrip("-").isdigit():
            ident = int(ident)
        if isinstance(ident, int):
            return cls.get_or_none(cls.chat_id == ident)
        return cls.get_or_none(cls.username == ident.lower())

    @classmethod
    async def update_chat(cls, chat: types.Chat, added_by_id: int | None = None):
        save_chat = await cls.get_chat(chat.id)
        username = chat.username.lower() if chat.username else None
        if not save_chat:
            save_chat = cls.create(
                chat_id=chat.id,
                chat_name=chat.title or chat.full_name or str(chat.id),
                chat_type=chat.type,
                username=username,
                added_by_id=added_by_id,
            )
        else:
            save_chat.chat_name = chat.title or chat.full_name or str(chat.id)
            save_chat.chat_type = chat.type
            save_chat.username = username
            if added_by_id is not None:
                save_chat.added_by_id = added_by_id
            save_chat.updated_at = datetime.now()
            save_chat.save()
        return save_chat

    @classmethod
    async def mark_deleted(cls, chat: types.Chat):
        save_chat = await cls.update_chat(chat)
        save_chat.is_deleted = True
        save_chat.updated_at = datetime.now()
        save_chat.save()
        return save_chat

