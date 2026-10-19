import re

from aiogram import Bot
from aiogram.enums import MessageEntityType, StickerType
from aiogram.types import ChatPermissions, Message

from app.utils.text import escape_html

# дефолтные паки для базовой каптчи: ключ -> (название, эмодзи)
CAPTCHA_PACKS = {
    "fruits": ("Фрукты", ("🍎", "🍌", "🍇", "🍒", "🍉", "🍋", "🥝", "🍓", "🍑", "🍍", "🥥", "🍐")),
    "animals": ("Животные", ("🐶", "🐱", "🐸", "🐼", "🦊", "🐝", "🐢", "🐵", "🐷", "🐮", "🦁", "🐧")),
    "objects": ("Разное", ("⚽", "🎈", "🎸", "🚗", "✈️", "⭐", "🔥", "❄️", "🌙", "☂️", "🎁", "⏰")),
}
DEFAULT_CAPTCHA_PACK = "fruits"
CUSTOM_CAPTCHA_PACK = "custom"  # пак премиум-эмодзи, присланный админом

# текст кнопки с премиум-эмодзи: сам эмодзи рисуется иконкой, а пустой текст Telegram не принимает
CUSTOM_EMOJI_BUTTON_TEXT = "\u3164"
PACK_LINK = re.compile(r"(?:t\.me|telegram\.me)/addemoji/(\w+)")

OPTIONS_COUNT = 6  # сколько кнопок с эмодзи
STEPS = 2          # сколько раз нужно выбрать правильное эмодзи


DEFAULT_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


def emoji_html(emoji: tuple[str, str | None]) -> str:
    fallback, emoji_id = emoji
    if emoji_id is None:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{escape_html(fallback)}</tg-emoji>'


async def load_custom_pack(bot: Bot, message: Message) -> tuple[str, str, list[list[str]]]:
    """Достаёт пак премиум-эмодзи по ссылке t.me/addemoji/... или по эмодзи из сообщения.

    Возвращает (название, имя пака, [[fallback, custom_emoji_id], ...]).
    ValueError - если пак не подходит, TelegramBadRequest - если Telegram его не нашёл.
    """
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []

    name = None
    match = PACK_LINK.search(text)
    if match:
        name = match.group(1)
    else:
        emoji_ids = [entity.custom_emoji_id for entity in entities if entity.type == MessageEntityType.CUSTOM_EMOJI]
        if emoji_ids:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=emoji_ids[:1])
            name = stickers[0].set_name if stickers else None

    if not name:
        raise ValueError("Пришли ссылку вида t.me/addemoji/... или сообщение с премиум-эмодзи из пака.")

    sticker_set = await bot.get_sticker_set(name=name)
    if sticker_set.sticker_type != StickerType.CUSTOM_EMOJI:
        raise ValueError("Это пак стикеров, а нужен пак эмодзи.")

    emojis, seen = [], set()
    for sticker in sticker_set.stickers:
        if sticker.custom_emoji_id and sticker.custom_emoji_id not in seen:
            seen.add(sticker.custom_emoji_id)
            emojis.append([sticker.emoji or "⭐", sticker.custom_emoji_id])

    if len(emojis) < OPTIONS_COUNT:
        raise ValueError(f"В паке должно быть хотя бы {OPTIONS_COUNT} эмодзи.")
    return sticker_set.title, sticker_set.name, emojis


async def restrict_member(bot: Bot, chat_id: int, user_id: int):
    await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))


async def restore_permissions(bot: Bot, chat_id: int, user_id: int):
    chat = await bot.get_chat(chat_id)
    await bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=chat.permissions or DEFAULT_PERMISSIONS,
        use_independent_chat_permissions=True,
    )
