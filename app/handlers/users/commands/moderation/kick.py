from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from database.models.user import User

from app.filters.lulu import LuluFilter
from app.filters.setting import SettingEnable
from app.filters.is_chat_admin import IsChatAdmin, IsBotPermission
from app.utils.text import escape_html

from .utils import check_target, resolve_target, with_reason

router = Router(name="moderation_kick")


@router.message(LuluFilter(command=["кик"], ignore_name=True), SettingEnable("moderation"), IsChatAdmin(), IsBotPermission("restrict"))
async def kick_handler(message: Message, bot: Bot, lulu_text: str = ""):
    target, reason = await resolve_target(message, bot, lulu_text)
    if target is None:
        return await message.reply("Ответьте на сообщение пользователя, которого нужно кикнуть или укажите его.")

    if error := await check_target(message, bot, target, "кикнуть"):
        return await message.reply(error)

    target_member = await bot.get_chat_member(message.chat.id, target.id)
    if target_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        return await message.reply(f"{await User.get_name(target.id, True, target.first_name)} нет в чате.")

    # кик = бан + сразу разбан, чтобы пользователь мог вернуться
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target.id, only_if_banned=True)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        return await message.reply(f"Не удалось кикнуть: <code>{escape_html(e.message)}</code>")

    text = f"{await User.get_name(message.from_user.id, True, message.from_user.first_name)} Использует <b>Депульсо</b> и {await User.get_name(target.id, True, target.first_name)} вылетает из чата."
    await message.reply(with_reason(text, reason))
