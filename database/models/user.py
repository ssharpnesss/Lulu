from peewee import BigIntegerField, CharField, DateTimeField
from datetime import datetime

from database.loader import BaseModel

from aiogram import types

class User(BaseModel):
    user_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)

    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "users"

    @classmethod
    async def get_user(cls, ident: str | int):
        if str(ident).isdigit(): 
            ident = int(ident)

        if isinstance(ident, int):
            return cls.get_or_none(cls.user_id == ident)

        return cls.get_or_none(cls.username == ident.lower())

    @classmethod
    async def update_user(cls, user: types.User):
        save_user = await cls.get_user(user.id)
        username = user.username.lower() if user.username else None
        if not save_user:
            save_user = cls.create(
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=username
            )
        else:
            if save_user.first_name != user.first_name:
                save_user.first_name = user.first_name

            save_user.last_name = user.last_name
            save_user.username = username
            save_user.updated_at = datetime.now()
            save_user.save()