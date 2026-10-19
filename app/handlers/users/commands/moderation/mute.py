from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions
from aiogram.types import Message

from database.models.user import User

from app.filters.lulu import LuluFilter
from app.filters.setting import SettingEnable
from app.filters.is_chat_admin import IsChatAdmin, IsBotPermission
from app.utils.text import escape_html

from .utils import MUTE_PERMISSIONS, check_target, duration_phrase, get_until_date, parse_duration, resolve_target, with_reason

router = Router(name="moderation_mute")


@router.message(LuluFilter(command=["мут"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def mute_handler(message: Message, bot: Bot, lulu_text: str):
    target, lulu_text = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, которого нужно замутить или укажите его.")

    parsed = parse_duration(lulu_text)
    if parsed is None:
        return await message.reply(
            "Пример использования:\n"
            "<code>мут 1 час [причина] [юзер]</code>\n"
            "<code>мут навсегда [причина] [юзер]</code>"
        )
    seconds, duration_text, reason = parsed

    if error := await check_target(message, bot, target, "замутить"):
        return await message.reply(error)

    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=MUTE_PERMISSIONS,
            until_date=get_until_date(seconds),
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        return await message.reply(f"Не удалось замутить: <code>{escape_html(e.message)}</code>")

    text = f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} Использует <b>Силенцио</b> и {await User.get_name(target.id, True, target.first_name)} лишается права голоса {duration_phrase(duration_text)}."
    await message.reply(with_reason(text, reason))
    return


@router.message(LuluFilter(command=["размут", "анмут"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def unmute_handler(message: Message, bot: Bot, lulu_text: str = ""):

    target, _ = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, которого нужно размутить или укажите его.")

    target_member = await bot.get_chat_member(message.chat.id, target.id)
    if target_member.status != ChatMemberStatus.RESTRICTED or target_member.can_send_messages:
        return await message.reply(f"{await User.get_name(target.id, True, target.first_name)} не в муте.")

    chat = await bot.get_chat(message.chat.id)
    permissions = chat.permissions or ChatPermissions(can_send_messages=True)

    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=permissions,
            use_independent_chat_permissions=True,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        return await message.reply(f"Не удалось размутить: <code>{escape_html(e.message)}</code>")

    await message.reply(f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} Использует <b>Фините Инкантатем</b> и {await User.get_name(target.id, True, target.first_name)} снова может говорить.")
