from peewee import BigIntegerField, DateTimeField, TextField

from database.loader import BaseModel
from app.utils.time import get_now


class Warn(BaseModel):
    chat_id = BigIntegerField()
    user_id = BigIntegerField()
    admin_id = BigIntegerField()
    reason = TextField(null=True)

    created_at = DateTimeField(default=get_now)

    class Meta:
        table_name = "warns"
        indexes = ((("chat_id", "user_id"), False),)

    @classmethod
    async def add(cls, chat_id: int, user_id: int, admin_id: int, reason: str | None = None) -> int:
        cls.create(chat_id=chat_id, user_id=user_id, admin_id=admin_id, reason=reason or None)
        return await cls.count(chat_id, user_id)

    @classmethod
    async def count(cls, chat_id: int, user_id: int) -> int:
        return cls.select().where((cls.chat_id == chat_id) & (cls.user_id == user_id)).count()

    @classmethod
    async def get_warns(cls, chat_id: int, user_id: int) -> list["Warn"]:
        return list(
            cls.select()
            .where((cls.chat_id == chat_id) & (cls.user_id == user_id))
            .order_by(cls.created_at)
        )

    @classmethod
    async def remove_last(cls, chat_id: int, user_id: int) -> bool:
        last = (
            cls.select()
            .where((cls.chat_id == chat_id) & (cls.user_id == user_id))
            .order_by(cls.created_at.desc(), cls.id.desc())
            .first()
        )
        if last is None:
            return False
        last.delete_instance()
        return True

    @classmethod
    async def clear(cls, chat_id: int, user_id: int) -> int:
        return cls.delete().where((cls.chat_id == chat_id) & (cls.user_id == user_id)).execute()
