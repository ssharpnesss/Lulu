import math

from peewee import BigIntegerField, TextField, CharField

from database.loader import BaseModel

ANTIFLOOD_PARAMETERS = {
    "limit": ("Лимит сообщений", 5, 1000),
    "interval": ("Интервал (сек.)", 1.5, 86400),
    "warning_interval": ("Интервал предупреждений (сек.)", 5, 86400),
}


def parse_antiflood_parameter(parameter: str, value: str):
    _, _, maximum = ANTIFLOOD_PARAMETERS[parameter]
    number = float(value.strip().replace(",", "."))
    if not math.isfinite(number) or not 0 < number <= maximum:
        raise ValueError(f"Введите число больше 0 и не больше {maximum}.")
    if parameter == "limit":
        if not number.is_integer():
            raise ValueError("Лимит должен быть целым числом.")
        return int(number)
    return number

class SettingDescription(BaseModel):
    setting_key = CharField()
    short_name = TextField()
    description = TextField()
    status = TextField(default="public") # public | private(public - видят все, private - это настройки самого бота например текст что лулу будет писать при добавлении ее в чат) 

    button_emoji = TextField(null=True)

    class Meta:
        table_name = "setting_descriptions"

    @classmethod
    async def add_description(cls, setting_key: str, short_name: str, description: str):
        return cls.create(setting_key=setting_key, short_name=short_name, description=description)

    @classmethod
    async def get_description(cls, setting_key: str):
        return cls.get_or_none(cls.setting_key == setting_key)

    @classmethod
    async def get_all_descriptions(cls, status: str = "public"):
        return cls.select().where(cls.status == status)

class Setting(BaseModel):

    chat_id = BigIntegerField()
    setting_key = CharField()
    value = TextField(null=True)

    class Meta:
        table_name = "settings"
        
    @classmethod
    async def get_setting(cls, chat_id: int, setting_key: str):
        return cls.get_or_none((cls.chat_id == chat_id) & (cls.setting_key == setting_key))

    @classmethod
    async def set_setting(cls, chat_id: int, setting_key: str, value: str | None = None):
        setting = await cls.get_setting(chat_id, setting_key)
        if not setting:
            setting = cls.create(chat_id=chat_id, setting_key=setting_key, value=value)
        else:
            setting.value = value
            setting.save()
            
        return setting

    @classmethod
    async def get_setting_value(cls, chat_id: int, setting_key: str):
        setting = await cls.get_setting(chat_id, setting_key)
        return setting.value if setting else None

    @classmethod
    async def get_antiflood_parameters(cls, chat_id: int):
        values = {}
        for parameter, (_, default, _) in ANTIFLOOD_PARAMETERS.items():
            raw = await cls.get_setting_value(chat_id, f"antiflood_{parameter}")
            try:
                values[parameter] = parse_antiflood_parameter(parameter, raw) if raw is not None else default
            except ValueError:
                values[parameter] = default
        return values

    @classmethod
    async def is_enabled(cls, chat_id: int, setting_key: str):
        setting = await cls.get_setting(chat_id, setting_key)

        if setting_key == "welcome":
            return True if setting and setting.value is not None else False

        return True if setting and setting.value == "on" else False
