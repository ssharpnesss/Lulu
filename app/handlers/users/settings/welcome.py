from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

from app.utils.welcome import render_welcome
from database.models.chat import ChatMember
from database.models.setting import Setting

router = Router(name="new_chat_user")

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def new_chat_member_handler(event: types.ChatMemberUpdated):

    chat = event.chat
    new_member = event.new_chat_member
    await ChatMember.update_member(chat.id, new_member.user.id, "member")


    welcome = await Setting.get_setting_value(chat.id, "welcome")
    if welcome is None: return

    welcome_text = render_welcome(welcome, new_member.user, chat)
    try: await event.bot.send_message(chat.id, welcome_text)
    except: pass
    return 

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def leave_chat_member_handler(event: types.ChatMemberUpdated):

    chat = event.chat
    old_member = event.old_chat_member
    await ChatMember.update_member(chat.id, old_member.user.id, "left")

    parting = await Setting.get_setting_value(chat.id, "parting")
    if parting is None: return

    parting_text = render_welcome(parting, old_member.user, chat)
    try: await event.bot.send_message(chat.id, parting_text)
    except: pass


