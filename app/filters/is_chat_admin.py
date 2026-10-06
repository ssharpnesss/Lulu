from collections.abc import Iterable
from enum import Enum

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class Permission(str, Enum):
    can_delete_messages = "can_delete_messages"
    can_restrict_members = "can_restrict_members"
    can_pin_messages = "can_pin_messages"


PERMISSION_ALIASES: dict[str, Permission] = {
    alias: permission
    for permission, aliases in {
        Permission.can_delete_messages: (
            "delete", "del", "del_message", "del_msg", "del_m", "dm",
        ),
        Permission.can_pin_messages: (
            "pin", "pin_message", "pin_msg", "pin_m", "pm",
        ),
        Permission.can_restrict_members: (
            "restrict", "restrict_member", "restrict_m", "rm",
        ),
    }.items()
    for alias in aliases
}

class IsBotPermission(BaseFilter):
    def __init__(
        self,
        permissions: str | Permission | Iterable[str | Permission],
    ) -> None:
        if isinstance(permissions, (str, Permission)):
            permissions = [permissions]

        self.permissions = tuple(
            dict.fromkeys(self._parse_permission(p) for p in permissions)
        )

        if not self.permissions:
            raise ValueError("Необходимо указать права которые будут проверяться")

    @staticmethod
    def _parse_permission(value: str | Permission) -> Permission:
        if isinstance(value, Permission):
            return value

        if not isinstance(value, str):
            raise TypeError(
                f"Право должно быть строкой или Permission, "
                f"получено: {type(value).__name__}"
            )

        normalized = value.strip().lower()

        if normalized in PERMISSION_ALIASES:
            return PERMISSION_ALIASES[normalized]

        try:
            return Permission(normalized)
        except ValueError:
            raise ValueError(f"Неизвестное право бота: {value!r}") from None

    async def __call__(
        self,
        event: Message | CallbackQuery,
        bot: Bot,
    ) -> bool:
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            if event.message is None:
                return False
            chat_id = event.message.chat.id
        else:
            return False

        try:
            member = await bot.get_chat_member(
                chat_id=chat_id,
                user_id=bot.id,
            )
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            return False

        if member.status == ChatMemberStatus.CREATOR:
            return True

        if member.status != ChatMemberStatus.ADMINISTRATOR:
            return False

        result = [bool(getattr(member, permission.value, False)) for permission in self.permissions]
        return all(result)

class IsChatAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        message = event.message if isinstance(event, CallbackQuery) else event
        if not isinstance(message, Message) or message.chat.type == "private" or event.from_user is None:
            return False

        member = await event.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=event.from_user.id
        )

        allowed = member.status in ("creator", "administrator")
        if not allowed and isinstance(event, CallbackQuery):
            await event.answer("Настройки доступны ТОЛЬКО администраторам.", show_alert=True)
        return allowed
