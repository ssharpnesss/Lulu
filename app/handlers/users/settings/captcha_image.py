import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile, CallbackQuery, Message, User

from app.utils.captcha import restore_permissions
from app.utils.captcha_image import generate_code, render_captcha
from app.utils.emoji import get_emoji
from database.models.captcha import Captcha
from database.models.user import User as UserModel

from .keyboards.captcha_image_keyboard import ImageCaptchaKeyboard, image_captcha_invite_markup, image_captcha_refresh_markup
from .welcome import send_welcome

# Средний уровень: картинка с искажёнными символами. Пока каптча не пройдена,
# писать в чат нельзя, поэтому ответ отправляется боту в ЛС (deep link /start captcha_<chat_id>).

router = Router(name="captcha_image")
logger = logging.getLogger(__name__)


async def send_image_captcha_invite(bot: Bot, chat_id: int, user: User):
    captcha = await Captcha.start(chat_id, user.id, "image")

    me = await bot.me()
    message = await bot.send_message(
        chat_id,
        f"{get_emoji('protect')} {await UserModel.get_name(user.id, True, user.first_name)}, пройди каптчу, чтобы писать в чате.\n\n"
        f"Нажми кнопку ниже и отправь мне в ЛС символы с картинки.",
        reply_markup=image_captcha_invite_markup(me.username, chat_id),
    )
    captcha.chat_message_id = message.message_id
    captcha.save()


async def send_captcha_image(bot: Bot, captcha: Captcha):
    captcha.code = generate_code()
    captcha.save()
    await bot.send_photo(
        captcha.user_id,
        BufferedInputFile(render_captcha(captcha.code), filename="captcha.png"),
        caption="Отправь символы с картинки одним сообщением.",
        reply_markup=image_captcha_refresh_markup(captcha.chat_id),
    )


async def open_image_captcha(message: Message, chat_id: int):
    """Вызывается из /start captcha_<chat_id> в ЛС."""
    captcha = await Captcha.get_captcha(chat_id, message.from_user.id, "image")
    if captcha is None:
        return await message.answer("У тебя нет активной каптчи в этом чате.")

    await captcha.mark_solving()
    await send_captcha_image(message.bot, captcha)


@router.callback_query(ImageCaptchaKeyboard.filter(), F.message.chat.type == "private")
async def refresh_image_captcha_handler(callback: CallbackQuery, callback_data: ImageCaptchaKeyboard):
    captcha = await Captcha.get_captcha(callback_data.chat_id, callback.from_user.id, "image")
    if captcha is None:
        return await callback.answer("Эта каптча уже неактуальна.", show_alert=True)

    await captcha.mark_solving()
    await send_captcha_image(callback.bot, captcha)
    await callback.answer()


async def solving_captcha_filter(message: Message) -> bool | dict:
    if message.from_user is None: return False
    captcha = await Captcha.get_solving(message.from_user.id)
    return {"captcha": captcha} if captcha else False


@router.message(F.chat.type == "private", F.text, solving_captcha_filter)
async def image_captcha_answer_handler(message: Message, captcha: Captcha):
    user = message.from_user
    chat_id = captcha.chat_id

    answer = message.text.replace(" ", "").upper()
    if answer != captcha.code:
        await message.answer("Неверно, попробуй ещё раз.")
        return await send_captcha_image(message.bot, captcha)

    try:
        await restore_permissions(message.bot, chat_id, user.id)
    except TelegramAPIError:
        logger.exception("Каптча: не удалось вернуть права %s в чате %s", user.id, chat_id)
        return await message.answer("Не получилось выдать права, обратись к администратору чата.")

    await Captcha.remove(chat_id, user.id)

    if captcha.chat_message_id is not None:
        try:
            await message.bot.edit_message_text(
                f"{get_emoji('on_status')} {await UserModel.get_name(user.id, True, user.first_name)} прошёл каптчу и теперь может писать в чате.",
                chat_id=chat_id,
                message_id=captcha.chat_message_id,
            )
        except TelegramAPIError:
            logger.exception("Каптча: не удалось обновить сообщение в чате %s", chat_id)

    await message.answer("Каптча пройдена! Теперь можешь писать в чате.")

    try:
        chat = await message.bot.get_chat(chat_id)
    except TelegramAPIError:
        return logger.exception("Каптча: не удалось получить чат %s для приветствия", chat_id)
    await send_welcome(message.bot, chat, user)
