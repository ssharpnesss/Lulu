import logging

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

from app.utils.welcome import render_welcome
from database.models.captcha import Captcha
from database.models.chat import ChatMember, WelcomedUser
from database.models.setting import Setting
from app.filters.setting import SettingEnable

router = Router(name="new_chat_user")
logger = logging.getLogger(__name__)

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), SettingEnable("welcome"))
async def new_chat_member_handler(event: types.ChatMemberUpdated):

    chat = event.chat
    new_member = event.new_chat_member
    await ChatMember.update_member(chat.id, new_member.user.id, "member")

    # пользователь проходит каптчу - приветствие отправится после её прохождения
    if await Captcha.exists(chat.id, new_member.user.id): return

    await send_welcome(event.bot, chat, new_member.user)
    return 


async def send_welcome(bot: Bot, chat: types.Chat, user: types.User):
    if not await Setting.is_enabled(chat.id, "welcome"): return

    welcome = await Setting.get_setting_value(chat.id, "welcome")
    if welcome is None: return
    if not await WelcomedUser.mark(chat.id, user.id): return

    try:
        welcome_text = render_welcome(welcome, user, chat)
        await bot.send_message(chat.id, welcome_text)
    except (ValueError, TelegramAPIError):
        # не получилось - снимаем отметку, чтобы приветствие можно было отправить снова
        await WelcomedUser.unmark(chat.id, user.id)
        logger.exception("Приветствие: не удалось отправить в чат %s", chat.id)

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def leave_chat_member_handler(event: types.ChatMemberUpdated):

    chat = event.chat
    old_member = event.old_chat_member
    await ChatMember.update_member(chat.id, old_member.user.id, "left")

    if not await Setting.is_enabled(chat.id, "parting"): return
    parting = await Setting.get_setting_value(chat.id, "parting")

    try:
        parting_text = render_welcome(parting, old_member.user, chat)
        await event.bot.send_message(chat.id, parting_text)
    except (ValueError, TelegramAPIError):
        logger.exception("Прощание: не удалось отправить в чат %s", chat.id)
