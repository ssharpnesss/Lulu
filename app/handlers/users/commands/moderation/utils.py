import re
import datetime

from aiogram import Bot, types
from aiogram.enums import ChatMemberStatus, MessageEntityType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions, Message

from database.models.user import FACULTIES, User

from app.utils.text import escape_html

UNITS = {
    "second": (1, ("секунду", "секунды", "секунд")),
    "minute": (60, ("минуту", "минуты", "минут")),
    "hour": (3600, ("час", "часа", "часов")),
    "day": (86400, ("день", "дня", "дней")),
    "week": (7 * 86400, ("неделю", "недели", "недель")),
    "month": (30 * 86400, ("месяц", "месяца", "месяцев")),
    "year": (365 * 86400, ("год", "года", "лет")),
}

UNIT_ALIASES = {
    alias: unit
    for unit, aliases in {
        "second": ("с", "сек", "секунда", "секунды", "секунду", "секунд"),
        "minute": ("м", "мин", "минута", "минуты", "минуту", "минут"),
        "hour": ("ч", "час", "часа", "часов"),
        "day": ("д", "день", "дня", "дней", "сутки", "суток"),
        "week": ("н", "нед", "неделя", "недели", "неделю", "недель"),
        "month": ("мес", "месяц", "месяца", "месяцев"),
        "year": ("г", "год", "года", "лет"),
    }.items()
    for alias in aliases
}

FOREVER_ALIASES = ("навсегда", "вечно", "forever")

MIN_RESTRICT_SECONDS = 30
MAX_RESTRICT_SECONDS = 366 * 86400

WARN_LIMIT = 3
WARN_POINTS = 10


async def get_faculty(user_id: int) -> tuple[str, str]:
    _, faculty_to, faculty_of = FACULTIES[await User.get_faculty(user_id)]
    return faculty_to, faculty_of

DURATION_PATTERN = re.compile(r"^\s*(?:(\d+)\s*)?([^\W\d_]+)(?:\s+|$)(.*)$", re.DOTALL)

MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)


def plural(number: int, forms: tuple[str, str, str]) -> str:
    if number % 10 == 1 and number % 100 != 11:
        return forms[0]
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return forms[1]
    return forms[2]


def parse_duration(text: str) -> tuple[int | None, str, str] | None:
    """(секунды или None если навсегда, текст срока, остаток - причина) или None, если срок не распознан."""
    match = DURATION_PATTERN.match(text)
    if not match:
        return None

    number, word, rest = match.groups()
    word = word.casefold()

    if word in FOREVER_ALIASES and number is None:
        return None, "навсегда", rest.strip()

    unit = UNIT_ALIASES.get(word)
    if unit is None:
        return None

    amount = int(number) if number else 1
    if amount <= 0:
        return None

    seconds, forms = UNITS[unit]
    return amount * seconds, f"{amount} {plural(amount, forms)}", rest.strip()


async def resolve_target(message: Message, bot: Bot, text: str) -> tuple[types.User | None, str]:
    """(цель из реплая / text_mention / @username, текст без упоминания цели)."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user, text

    for entity in message.entities or []:
        if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
            return entity.user, text.replace(entity.extract_from(message.text), "", 1).strip()

        if entity.type == MessageEntityType.MENTION:
            raw = entity.extract_from(message.text)
            saved_user = await User.get_user(raw.lstrip("@"))
            if saved_user is None:
                return None, text
            try:
                member = await bot.get_chat_member(message.chat.id, saved_user.user_id)
            except TelegramBadRequest:
                return None, text
            return member.user, text.replace(raw, "", 1).strip()

    return None, text


async def check_target(message: Message, bot: Bot, target: types.User, action: str) -> str | None:
    """Текст ошибки, если цель нельзя наказать, иначе None. action - глагол: «замутить», «забанить»..."""
    if target.id == bot.id:
        return f"Себя {action} я не могу."
    if target.id == message.from_user.id:
        return f"Себя {action} нельзя."

    try:
        target_member = await bot.get_chat_member(message.chat.id, target.id)
    except TelegramBadRequest:
        return None
    if target_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
        return f"Администратора {action} нельзя."
    return None


def get_until_date(seconds: int | None) -> datetime.datetime | None:
    """None - навсегда (Telegram считает навсегда срок меньше 30 секунд или больше 366 дней)."""
    if seconds is None or seconds > MAX_RESTRICT_SECONDS:
        return None
    seconds = max(seconds, MIN_RESTRICT_SECONDS + 1)
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)


def duration_phrase(duration_text: str) -> str:
    return "навсегда" if duration_text == "навсегда" else "на " + duration_text


def with_reason(text: str, reason: str | None) -> str:
    if reason:
        text += f"\n<b>Причина:</b> {escape_html(reason)}"
    return text


async def ban_user(message: Message, bot: Bot, target: types.User, seconds: int | None) -> str | None:
    """Банит цель, возвращает текст ошибки или None."""
    try:
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            until_date=get_until_date(seconds),
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        return f"Не удалось забанить: <code>{escape_html(e.message)}</code>"
    return None
