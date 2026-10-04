import html
import re

from aiogram.types import User

PLACEHOLDERS = {"имя", "фамилия", "ид", "айди", "имяфамилия"}
PATTERN = re.compile(r"\{([^{}\n]+)\}")


def render_welcome(template: str, user: User) -> str:
    values = {
        "имя": user.first_name,
        "фамилия": user.last_name or "",
        "ид": str(user.id),
        "айди": str(user.id),
        "имяфамилия": user.full_name,
    }
    def replace(match):
        key = match.group(1)
        if key not in PLACEHOLDERS:
            raise ValueError(f"Неизвестная подстановка: {{{key}}}")
        return html.escape(values[key], quote=True)
    return PATTERN.sub(replace, template)
