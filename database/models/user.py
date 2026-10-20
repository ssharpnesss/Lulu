import random
import string

from peewee import BigIntegerField, CharField, DateTimeField, BooleanField, TextField
from aiogram import types

from database.loader import BaseModel
from app.utils.time import get_now
from app.utils.text import escape_html


FACULTIES = {
    "gryffindor": ("Гриффиндор", "Гриффиндору", "Гриффиндора"),
    "slytherin": ("Слизерин", "Слизерину", "Слизерина"),
    "ravenclaw": ("Когтевран", "Когтеврану", "Когтеврана"),
    "hufflepuff": ("Пуффендуй", "Пуффендую", "Пуффендуя"),
}


def random_faculty() -> str:
    return random.choice(list(FACULTIES))

def _generate_uuid(min_size: int = 4, max_size: int = 7):
    _size = random.randint(min_size, max_size)
    key = None
    while not key:
        _key = "".join(random.choices(string.ascii_letters + string.digits, k=_size))
        if not User.get_or_none(User.u_user_id == _key):
            key = _key
            break
    return key


class User(BaseModel):

    u_user_id = CharField(unique=True, default=_generate_uuid)
    user_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)
    pm = BooleanField(default=False)
    faculty = CharField(null=True, default=random_faculty)

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
                name = f"<a href='tg://openmessage?user_id={ident}'>{escape_html(default_name)}</a>"

            return name if name else default_name

        return user.first_name if user else default_name

    @classmethod
    async def get_faculty(cls, user_id: int) -> str:
        user = cls.get_or_none(cls.user_id == user_id)
        if user and user.faculty in FACULTIES:
            return user.faculty
        keys = list(FACULTIES)
        return keys[user_id % len(keys)]

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
                u_user_id=cls._generate_u_user_id(),
                user_id=user.id,
                first_name=escape_html(user.first_name),
                last_name=escape_html(user.last_name) if user.last_name else None,
                username=username,
                pm=is_pm
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

class Magic(BaseModel):
    user_id = BigIntegerField(unique=True)
    file_id = TextField()
    command = CharField()
    value = CharField()

    created_at = DateTimeField(default=get_now)
    updated_at = DateTimeField(default=get_now)

    @classmethod
    async def add_magic(
        cls, user_id: int, file_id: str, command: str, value: str
    ):
        # лимит магий внехогвартса - 2
        info = cls.select().where(cls.user_id == user_id)
        if len(info) >= 2:
            return 'limit'

        cls.create(

        )