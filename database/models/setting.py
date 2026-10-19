import json
import math

from peewee import BigIntegerField, TextField, CharField

from database.loader import BaseModel
from app.utils.captcha import CAPTCHA_PACKS, CUSTOM_CAPTCHA_PACK, DEFAULT_CAPTCHA_PACK, OPTIONS_COUNT

ANTIFLOOD_PARAMETERS = {
    "limit": ("Лимит сообщений", 5, 1000),
    "interval": ("Интервал (сек.)", 1.5, 86400),
}

CAPTCHA_LEVELS = {
    "basic": "Базовый",
    "medium": "Средний",
    "advanced": "Продвинутый",
}
CAPTCHA_IMPLEMENTED_LEVELS = {"basic", "medium"}
DEFAULT_CAPTCHA_LEVEL = "basic"

# настройки, где в value хранится текст: включено - value = текст, выключено - value = "off"
TEXT_SETTINGS = {"welcome", "parting"}

# настройки, включенные пока админ явно их не выключил
DEFAULT_ON_SETTINGS = {"moderation"}


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
    async def get_captcha_level(cls, chat_id: int) -> str:
        level = await cls.get_setting_value(chat_id, "captcha_level")
        return level if level in CAPTCHA_IMPLEMENTED_LEVELS else DEFAULT_CAPTCHA_LEVEL

    @classmethod
    async def get_captcha_custom_pack(cls, chat_id: int) -> dict | None:
        """Присланный админом пак: {"name", "title", "emojis": [[fallback, custom_emoji_id], ...]}."""
        raw = await cls.get_setting_value(chat_id, "captcha_custom_pack")
        try:
            pack = json.loads(raw) if raw else None
        except ValueError:
            return None
        return pack if pack and len(pack.get("emojis", [])) >= OPTIONS_COUNT else None

    @classmethod
    async def set_captcha_custom_pack(cls, chat_id: int, name: str, title: str, emojis: list[list[str]]):
        pack = {"name": name, "title": title, "emojis": emojis}
        await cls.set_setting(chat_id, "captcha_custom_pack", json.dumps(pack, ensure_ascii=False))
        await cls.set_setting(chat_id, "captcha_pack", CUSTOM_CAPTCHA_PACK)

    @classmethod
    async def get_captcha_pack(cls, chat_id: int) -> str:
        pack = await cls.get_setting_value(chat_id, "captcha_pack")
        if pack == CUSTOM_CAPTCHA_PACK and await cls.get_captcha_custom_pack(chat_id):
            return pack
        return pack if pack in CAPTCHA_PACKS else DEFAULT_CAPTCHA_PACK

    @classmethod
    async def get_captcha_emojis(cls, chat_id: int) -> list[tuple[str, str | None]]:
        """Эмодзи для базовой каптчи чата: (fallback, custom_emoji_id или None)."""
        pack = await cls.get_captcha_pack(chat_id)
        if pack == CUSTOM_CAPTCHA_PACK:
            custom = await cls.get_captcha_custom_pack(chat_id)
            return [(fallback, emoji_id) for fallback, emoji_id in custom["emojis"]]
        return [(emoji, None) for emoji in CAPTCHA_PACKS[pack][1]]

    @classmethod
    async def is_enabled(cls, chat_id: int, setting_key: str):
        setting = await cls.get_setting(chat_id, setting_key)

        if setting_key in TEXT_SETTINGS:
            return True if setting and setting.value not in (None, "off") else False

        if setting_key in DEFAULT_ON_SETTINGS:
            return not (setting and setting.value == "off")

        return True if setting and setting.value == "on" else False

    @classmethod
    async def set_enabled(cls, chat_id: int, setting_key: str, enabled: bool) -> bool:
        """False - если текстовую настройку нельзя включить, потому что текст не задан."""
        if setting_key in TEXT_SETTINGS and enabled:
            # включается только заданием текста
            return await cls.is_enabled(chat_id, setting_key)

        await cls.set_setting(chat_id, setting_key, "on" if enabled else "off")
        return True

    @classmethod
    async def get_disabled_commands(cls, chat_id: int) -> set[str]:
        raw = await cls.get_setting_value(chat_id, "disabled_commands")
        return set(raw.split(",")) - {""} if raw else set()

    @classmethod
    async def is_command_disabled(cls, chat_id: int, key: str) -> bool:
        return key in await cls.get_disabled_commands(chat_id)

    @classmethod
    async def set_command_disabled(cls, chat_id: int, key: str, disabled: bool):
        keys = await cls.get_disabled_commands(chat_id)
        keys.add(key) if disabled else keys.discard(key)
        await cls.set_setting(chat_id, "disabled_commands", ",".join(sorted(keys)) or None)
