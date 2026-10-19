import logging

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message, User

from app.filters.is_chat_admin import IsBotPermission
from app.filters.setting import SettingEnable
from app.utils.captcha import STEPS, emoji_html, restore_permissions, restrict_member
from app.utils.emoji import get_emoji
from database.models.captcha import Captcha
from database.models.user import User as UserModel
from database.models.setting import Setting

from .keyboards.captcha_keyboard import CaptchaKeyboard, captcha_markup
from .captcha_image import send_image_captcha_invite
from .welcome import send_welcome

router = Router(name="captcha")
logger = logging.getLogger(__name__)


async def captcha_text(captcha: Captcha, user: User) -> str:
    return (
        f"{get_emoji('protect')} {await UserModel.get_name(user.id, True, user.first_name)}, пройди каптчу, чтобы писать в чате.\n\n"
        f"Выбери это эмодзи: {emoji_html(captcha.target_emoji)}\n"
        f"Шаг {captcha.step + 1}/{STEPS}"
    )


async def show_captcha(message: Message, captcha: Captcha, user: User):
    try:
        await message.edit_text(await captcha_text(captcha, user), reply_markup=captcha_markup(captcha))
    except TelegramAPIError:
        logger.exception("Каптча: не удалось обновить сообщение в чате %s", captcha.chat_id)


@router.chat_member(
    ChatMemberUpdatedFilter(JOIN_TRANSITION),
    # restricted - если вышел, не пройдя каптчу: ограничение сохраняется при перезаходе
    F.new_chat_member.status.in_({"member", "restricted"}),
    F.new_chat_member.user.is_bot == False,
    SettingEnable("captcha"),
    IsBotPermission("restrict"),
)
async def captcha_join_handler(event: ChatMemberUpdated):
    chat_id = event.chat.id
    user = event.new_chat_member.user

    try:
        await restrict_member(event.bot, chat_id, user.id)
    except TelegramAPIError:
        logger.exception("Каптча: не удалось ограничить %s в чате %s", user.id, chat_id)
        raise SkipHandler()

    level = await Setting.get_captcha_level(chat_id)
    try:
        if level == "medium":
            await send_image_captcha_invite(event.bot, chat_id, user)
        else:
            captcha = await Captcha.start(chat_id, user.id, "emoji", await Setting.get_captcha_emojis(chat_id))
            await event.bot.send_message(chat_id, await captcha_text(captcha, user), reply_markup=captcha_markup(captcha))
    except TelegramAPIError:
        logger.exception("Каптча: не удалось отправить каптчу в чате %s", chat_id)

    # передаём событие дальше, чтобы сработало приветствие
    raise SkipHandler()


@router.callback_query(CaptchaKeyboard.filter())
async def captcha_answer_handler(callback: CallbackQuery, callback_data: CaptchaKeyboard):
    message = callback.message
    if not isinstance(message, Message):
        return await callback.answer()

    user = callback.from_user
    if callback_data.user_id != user.id:
        return await callback.answer("Эта каптча не для тебя.", show_alert=True)

    emojis = await Setting.get_captcha_emojis(message.chat.id)
    captcha = await Captcha.get_captcha(message.chat.id, user.id, "emoji")
    if captcha is None:
        # каптчи нет в БД - начинаем заново
        captcha = await Captcha.start(message.chat.id, user.id, "emoji", emojis)
        await show_captcha(message, captcha, user)
        return await callback.answer("Каптча обновлена, попробуй ещё раз.", show_alert=True)

    if callback_data.index != captcha.target:
        captcha.step = 0
        captcha.new_round(emojis)
        captcha.save()
        await show_captcha(message, captcha, user)
        return await callback.answer("Неверно! Начни сначала.", show_alert=True)

    captcha.step += 1
    if captcha.step < STEPS:
        captcha.new_round(emojis)
        captcha.save()
        await show_captcha(message, captcha, user)
        return await callback.answer("Верно!")

    try:
        await restore_permissions(callback.bot, message.chat.id, user.id)
    except TelegramAPIError:
        logger.exception("Каптча: не удалось вернуть права %s в чате %s", user.id, message.chat.id)
        return await callback.answer("Не получилось выдать права, обратись к администратору.", show_alert=True)

    await Captcha.remove(message.chat.id, user.id)
    try:
        await message.edit_text(f"{get_emoji('on_status')} {await UserModel.get_name(user.id, True, user.first_name)} прошёл каптчу и теперь может писать в чате.")
    except TelegramAPIError:
        logger.exception("Каптча: не удалось обновить сообщение в чате %s", message.chat.id)
    await callback.answer("Каптча пройдена!")
    await send_welcome(callback.bot, message.chat, user)
