from peewee import BigIntegerField, BooleanField, CharField, DateTimeField, TextField
from aiogram import types

from database.loader import BaseModel
from app.utils.time import get_now

import random
import string

def _generate_uuid(min_size: int = 7, max_size: int = 10):
    _size = random.randint(min_size, max_size)
    key = None
    while not key:
        _key = "".join(random.choices(string.ascii_letters + string.digits, k=_size))
        if not Chat.get_or_none(Chat.u_chat_id == _key):
            key = _key
            break
    return key


class ChatMember(BaseModel):

    chat_id = BigIntegerField()
    user_id = BigIntegerField()
    status = CharField(default="member") # member | restricted | admin | creator | leave
    
    created_at = DateTimeField(default=get_now)
    updated_at = DateTimeField(default=get_now)

    class Meta:
        db_table = "chat_members"
        indexes = ((("chat_id", "user_id"), True),)

    @classmethod
    async def get_member(cls, chat_id: int, user_id: int):
        return cls.get_or_none((cls.chat_id == chat_id) & (cls.user_id == user_id))

    @classmethod
    async def update_member(cls, chat_id: int, user_id: int, status: str):
        member = await cls.get_member(chat_id, user_id)
        if not member:
            member = cls.create(chat_id=chat_id, user_id=user_id, status=status)
        else:
            if member.status != status:
                member.status = status
                member.updated_at = get_now()
                member.save()


        

class Chat(BaseModel):

    u_chat_id = CharField(unique=True, default=_generate_uuid)

    chat_id = BigIntegerField(unique=True)
    owner_id = BigIntegerField(null=True)
    added_by_id = BigIntegerField(null=True)
    chat_name = CharField(255)
    chat_type = CharField(default="group")
    username = CharField(null=True)
    is_deleted = BooleanField(default=False)

    created_at = DateTimeField(default=get_now)
    updated_at = DateTimeField(default=get_now)

    @classmethod
    async def get_chat(cls, ident: str | int):
        if str(ident).lstrip("-").isdigit():
            ident = int(ident)
        if isinstance(ident, int):
            return cls.get_or_none(cls.chat_id == ident)

        result = cls.get_or_none(cls.u_chat_id == ident)
        if result: return result

        return cls.get_or_none(cls.username == ident.lower())

    @classmethod
    async def update_chat(cls, chat: types.Chat, added_by_id: int | None = None):
        save_chat = await cls.get_chat(chat.id)
        username = chat.username.lower() if chat.username else None
        if not save_chat:
            save_chat = cls.create(
                u_chat_id=cls._generate_u_chat_id(),
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
            save_chat.updated_at = get_now()
            save_chat.save()
        return save_chat

    @classmethod
    async def mark_deleted(cls, chat: types.Chat):
        save_chat = await cls.update_chat(chat)
        save_chat.is_deleted = True
        save_chat.updated_at = get_now()
        save_chat.save()
        return save_chat



class WelcomedUser(BaseModel):
    chat_id = BigIntegerField()
    user_id = BigIntegerField()

    created_at = DateTimeField(default=get_now)

    class Meta:
        table_name = "welcomed_users"
        indexes = ((("chat_id", "user_id"), True),)

    @classmethod
    async def mark(cls, chat_id: int, user_id: int) -> bool:
        """Запоминает приветствие. False - если пользователя уже приветствовали."""
        _, created = cls.get_or_create(chat_id=chat_id, user_id=user_id)
        return created

    @classmethod
    async def unmark(cls, chat_id: int, user_id: int) -> int:
        return cls.delete().where((cls.chat_id == chat_id) & (cls.user_id == user_id)).execute()

    @classmethod
    async def clear(cls, chat_id: int) -> int:
        return cls.delete().where(cls.chat_id == chat_id).execute()
