from peewee import BigIntegerField, BooleanField, CharField

from database.loader import BaseModel


class Protects(BaseModel):
    chat_id = BigIntegerField()
    protection = CharField()
    enabled = BooleanField(default=False)

    class Meta:
        table_name = "protects"
        
    @classmethod
    async def get_protection(cls, chat_id: int, protection: str):
        return cls.get_or_none((cls.chat_id == chat_id) & (cls.protection == protection))

    @classmethod
    async def set_protection(cls, chat_id: int, protection: str, enabled: bool):
        setting = await cls.get_protection(chat_id, protection)
        if not setting:
            setting = cls.create(chat_id=chat_id, protection=protection, enabled=enabled)
        else:
            setting.enabled = enabled
            setting.save()
            
        return setting

    @classmethod
    async def is_enabled(cls, chat_id: int, protection: str):
        setting = await cls.get_protection(chat_id, protection)
        return setting.enabled if setting else False
