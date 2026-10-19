import json
import random

from peewee import BigIntegerField, BooleanField, CharField, DateTimeField, IntegerField, TextField

from database.loader import BaseModel
from app.utils.time import get_now
from app.utils.captcha import OPTIONS_COUNT


class Captcha(BaseModel):
    chat_id = BigIntegerField()
    user_id = BigIntegerField()
    kind = CharField(default="emoji")  # emoji | image

    # emoji: текущий шаг, варианты на кнопках (JSON-список [fallback, custom_emoji_id]) и индекс правильного
    step = IntegerField(default=0)
    options = TextField(default="[]")
    target = IntegerField(default=0)

    # image: код с картинки, сообщение с кнопкой «Пройти каптчу» в чате
    # и флаг, что пользователь сейчас решает эту каптчу в ЛС бота
    code = CharField(default="")
    chat_message_id = BigIntegerField(null=True)
    solving = BooleanField(default=False)

    created_at = DateTimeField(default=get_now)

    class Meta:
        table_name = "captchas"
        indexes = ((("chat_id", "user_id"), True),)

    @property
    def option_list(self) -> list[tuple[str, str | None]]:
        # старые каптчи хранили варианты просто строками
        return [(option, None) if isinstance(option, str) else tuple(option) for option in json.loads(self.options)]

    @property
    def target_emoji(self) -> tuple[str, str | None]:
        return self.option_list[self.target]

    def new_round(self, emojis: list[tuple[str, str | None]]):
        self.options = json.dumps(random.sample(emojis, OPTIONS_COUNT), ensure_ascii=False)
        self.target = random.randrange(OPTIONS_COUNT)

    @classmethod
    async def get_captcha(cls, chat_id: int, user_id: int, kind: str | None = None):
        query = (cls.chat_id == chat_id) & (cls.user_id == user_id)
        if kind is not None:
            query &= cls.kind == kind
        return cls.get_or_none(query)

    @classmethod
    async def exists(cls, chat_id: int, user_id: int) -> bool:
        return cls.select().where((cls.chat_id == chat_id) & (cls.user_id == user_id)).exists()

    @classmethod
    async def start(cls, chat_id: int, user_id: int, kind: str, emojis: list[tuple[str, str | None]] | None = None):
        """Создаёт новую каптчу, заменяя старую для этого пользователя в чате."""
        await cls.remove(chat_id, user_id)
        captcha = cls(chat_id=chat_id, user_id=user_id, kind=kind)
        if kind == "emoji":
            captcha.new_round(emojis)
        captcha.save()
        return captcha

    @classmethod
    async def remove(cls, chat_id: int, user_id: int) -> int:
        return cls.delete().where((cls.chat_id == chat_id) & (cls.user_id == user_id)).execute()

    @classmethod
    async def get_solving(cls, user_id: int):
        """Каптча с картинкой, которую пользователь сейчас решает в ЛС."""
        return cls.get_or_none((cls.user_id == user_id) & (cls.kind == "image") & (cls.solving == True))

    async def mark_solving(self):
        """Делает эту каптчу активной в ЛС, снимая флаг с остальных каптч пользователя."""
        type(self).update(solving=False).where(type(self).user_id == self.user_id).execute()
        self.solving = True
        self.save()
