import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, IS_ADMIN
from aiogram.types import ChatMemberUpdated
from database.models.chats import Chats

router = Router()
logger = logging.getLogger(__name__)


async def save_chat(event: ChatMemberUpdated):
    if event.chat.type in {"group", "supergroup", "channel"}:
        chat = await Chats.update_chat(event.chat, added_by_id=event.from_user.id)
        chat.is_deleted = False
        chat.owner_id = None
        chat.updated_at = datetime.now()
        chat.save()
        try:
            administrators = await event.bot.get_chat_administrators(event.chat.id)
        except TelegramAPIError:
            logger.exception("Could not fetch owner of chat %s", event.chat.id)
        else:
            owner = next((member for member in administrators if member.status == "creator"), None)
            if owner is not None:
                chat.owner_id = owner.user.id
                chat.save()

@router.my_chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER),
    F.new_chat_member.status != "administrator",
)
async def new_chat_for_lulu(event: ChatMemberUpdated):
    await save_chat(event)
    await event.answer(
        "Привет! Я - <b>Lulu.</b>\n"
        "Спасибо, что добавили меня в свой чат :)"
    )

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_ADMIN))
async def bot_added_as_admin(event: ChatMemberUpdated):
    await save_chat(event)
    await event.answer(
        "Привет! Я - <b>Lulu.</b>\n"
        "Спасибо, что добавили меня в свой чат :)\n"
        "Ого, еще и права администратора сразу дали мухаха))"
    )

@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_has_beed_kicked(event: ChatMemberUpdated):
    await Chats.mark_deleted(event.chat)
