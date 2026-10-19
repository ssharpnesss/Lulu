from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from database.models.user import User

from app.filters.lulu import LuluFilter
from app.filters.setting import SettingEnable
from app.filters.is_chat_admin import IsChatAdmin, IsBotPermission
from app.utils.text import escape_html

from .utils import ban_user, check_target, duration_phrase, parse_duration, resolve_target, with_reason

router = Router(name="moderation_ban")


@router.message(LuluFilter(command=["бан"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def ban_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, lulu_text = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply(
            "Ответьте на сообщение пользователя, которого нужно забанить или укажите его.\n\n"
            "Пример использования:\n"
            "<code>бан [причина] [юзер]</code>\n"
            "<code>бан 1 день [причина] [юзер]</code>"
        )

    # срок необязателен: без него бан навсегда, а весь текст - причина
    parsed = parse_duration(lulu_text)
    seconds, duration_text, reason = parsed if parsed else (None, "навсегда", lulu_text.strip())

    if error := await check_target(message, bot, target, "забанить"):
        return await message.reply(error)

    if error := await ban_user(message, bot, target, seconds):
        return await message.reply(error)

    text = f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} Использует <b>Авада Кедавра</b> и {await User.get_name(target.id, True, target.first_name)} изгнан из чата {duration_phrase(duration_text)}."
    await message.reply(with_reason(text, reason))


@router.message(LuluFilter(command=["разбан", "анбан"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def unban_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, _ = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, которого нужно разбанить или укажите его.")

    target_member = await bot.get_chat_member(message.chat.id, target.id)
    if target_member.status != ChatMemberStatus.KICKED:
        return await message.reply(f"{await User.get_name(target.id, True, target.first_name)} не в бане.")

    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target.id, only_if_banned=True)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        return await message.reply(f"Не удалось разбанить: <code>{escape_html(e.message)}</code>")

    await message.reply(f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} Использует <b>Ренервейт</b> и {await User.get_name(target.id, True, target.first_name)} снова может войти в чат.")
