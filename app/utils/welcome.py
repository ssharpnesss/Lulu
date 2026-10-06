import html
import re

from aiogram.types import User, Chat
from app.utils.time import get_now
from app.utils.text import escape_html

PLACEHOLDERS = {
    "имя", "фамилия", "имяфамилия",
    "тэг", "тег", "ментион", "упоминание"
    "ид", "айди", 
    "юзер", "юзернейм", 
    "датавремя", "время", "дата",
    "название", "тайтл", "титле", "чатназвание",
    "чатид", "идчат", "чатайди", "айдичат"
}
PATTERN = re.compile(r"\{([^{}\n]+)\}")
TAG_KEYS = ["тэг", "тег", "ментион", "упоминание"]

def render_welcome(template: str, user: User, chat: Chat) -> str:

    mention = (
        f"<a href='tg://openmessage?user_id={user.id}'>{escape_html(user.first_name)}</a>" 
        if user.username is None else 
        f"<a href='https://t.me/{user.username}'>{escape_html(user.first_name)}</a>"
    )
    tag = f"<a href='tg://user?id={user.id}'>{escape_html(user.first_name)}</a>"

    values = {
        "имя": user.first_name or "",
        "фамилия": user.last_name or "",
        "имяфамилия": user.full_name or "",

        "тэг": mention,
        "тег": mention,
        "ментион": mention,
        "упоминание": tag,

        "ид": str(user.id),
        "айди": str(user.id),
        "юзер": f"@{user.username}" if user.username else "",
        "юзернейм": f"@{user.username}" if user.username else "",

        "название": chat.title or "",
        "чатназвание": chat.title or "",
        "тайтл": chat.title or chat.full_name or str(chat.id),
        "титле": chat.title or chat.full_name or str(chat.id),
        "чатид": str(chat.id),
        "идчат": str(chat.id),
        "чатайди": str(chat.id),
        "айдичат": str(chat.id),

        "датавремя": get_now().strftime("%Y/%m/%d %H:%M"),
        "время": get_now().time().strftime("%H:%M"),
        "дата": get_now().date().strftime("%Y/%m/%d"),
    }
    def replace(match):
        key = match.group(1)
        if key not in PLACEHOLDERS:
            raise ValueError(f"Неизвестная подстановка: {{{key}}}")
        if key in TAG_KEYS:
            return values[key]
        return html.escape(values[key], quote=True)
    return PATTERN.sub(replace, template)
