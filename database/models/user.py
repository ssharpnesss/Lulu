from peewee import BigIntegerField, CharField, DateTimeField, BooleanField
from aiogram import types

from database.loader import BaseModel
from app.utils.time import get_now
from app.utils.text import escape_html



class User(BaseModel):
    user_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)
    pm = BooleanField(default=False) 

    created_at = DateTimeField(default=get_now)
    updated_at = DateTimeField(default=get_now)

    class Meta:
        table_name = "users"

    @classmethod
    async def get_name(cls, ident: str | int, is_mention: bool = False, default_name: str = "Неизвестный"):
        if str(ident).isdigit(): 
            ident = int(ident)

        if isinstance(ident, int): user = cls.get_or_none(cls.user_id == ident)
        else: user = cls.get_or_none(cls.username == ident.lower())

        if is_mention:
            name = None
            if user:
                if user.username: name = f"<a href='https://t.me/{user.username}'>{user.first_name}</a>"
                else: name = f"<a href='tg://openmessage?user_id={user.user_id}'>{user.first_name}</a>"
            else:
                name = f"<a href='tg://openmessage?user_id={ident}'>{default_name}</a>"

            return name if name else default_name

        return user.first_name if user else default_name

    @classmethod
    async def get_user(cls, ident: str | int):
        if str(ident).isdigit(): 
            ident = int(ident)

        if isinstance(ident, int):
            return cls.get_or_none(cls.user_id == ident)

        return cls.get_or_none(cls.username == ident.lower())

    @classmethod
    async def update_user(cls, user: types.User, is_pm: bool = False):
        save_user = await cls.get_user(user.id)
        username = user.username.lower() if user.username else None
        if not save_user:
            save_user = cls.create(
                user_id=user.id,
                first_name=escape_html(user.first_name),
                last_name=escape_html(user.last_name) if user.last_name else None,
                username=username
            )
        else:
            if save_user.first_name != escape_html(user.first_name):
                save_user.first_name = escape_html(user.first_name)

            if is_pm:
                save_user.pm = True

            save_user.last_name = escape_html(user.last_name) if user.last_name else None
            save_user.username = username
            save_user.updated_at = get_now()
            save_user.save()