from aiogram import Bot, Router
from aiogram.types import Message

from database.models.warn import Warn
from database.models.user import User

from app.filters.lulu import LuluFilter
from app.filters.setting import SettingEnable
from app.filters.is_chat_admin import IsChatAdmin, IsBotPermission
from app.utils.text import escape_html

from .utils import WARN_LIMIT, WARN_POINTS, ban_user, check_target, get_faculty, resolve_target, with_reason

router = Router(name="moderation_warn")


@router.message(LuluFilter(command=["пред", "варн"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def warn_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, reason = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, которому нужно выдать предупреждение или укажите его.")

    if error := await check_target(message, bot, target, "предупредить"):
        return await message.reply(error)

    count = await Warn.add(message.chat.id, target.id, message.from_user.id, reason)

    faculty_to, _ = await get_faculty(target.id)
    text = f"<b>Минус {WARN_POINTS} очков {faculty_to}!</b> {await User.get_name(target.id, True, target.first_name)} получает предупреждение <b>{count}/{WARN_LIMIT}</b>."
    text = with_reason(text, reason)

    if count >= WARN_LIMIT:
        if error := await ban_user(message, bot, target, None):
            return await message.reply(f"{text}\n\n{error}")
        await Warn.clear(message.chat.id, target.id)
        text += f"\n\nЛимит предупреждений исчерпан - {await User.get_name(target.id, True, target.first_name)} изгнан из чата навсегда."

    await message.reply(text)


@router.message(LuluFilter(command=["снять пред", "разварн", "анварн"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin())
async def unwarn_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, _ = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, с которого нужно снять предупреждение или укажите его.")

    if not await Warn.remove_last(message.chat.id, target.id):
        return await message.reply(f"У {await User.get_name(target.id, True, target.first_name)} нет предупреждений.")

    count = await Warn.count(message.chat.id, target.id)
    faculty_to, _ = await get_faculty(target.id)
    await message.reply(
        f"<b>{WARN_POINTS} очков возвращено {faculty_to}!</b> "
        f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} снимает с {await User.get_name(target.id, True, target.first_name)} предупреждение. Осталось <b>{count}/{WARN_LIMIT}</b>."
    )


@router.message(LuluFilter(command=["преды", "варны"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin())
async def warns_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, _ = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя или укажите его.")

    warns = await Warn.get_warns(message.chat.id, target.id)
    if not warns:
        return await message.reply(f"У {await User.get_name(target.id, True, target.first_name)} нет предупреждений.")

    _, faculty_of = await get_faculty(target.id)
    lines = [
        f"Предупреждения {await User.get_name(target.id, True, target.first_name)} <b>{len(warns)}/{WARN_LIMIT}</b> "
        f"(из-за него у {faculty_of} минус {len(warns) * WARN_POINTS} очков):"
    ]
    for number, warn in enumerate(warns, 1):
        lines.append(f"{number}. {escape_html(warn.reason) if warn.reason else 'без причины'}")
    await message.reply("\n".join(lines))
