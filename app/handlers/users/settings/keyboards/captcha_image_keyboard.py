from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

DEEP_LINK_PREFIX = "captcha_"


class ImageCaptchaKeyboard(CallbackData, prefix="icaptcha"):
    chat_id: int


def image_captcha_invite_markup(bot_username: str, chat_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Пройти каптчу", url=f"https://t.me/{bot_username}?start={DEEP_LINK_PREFIX}{chat_id}")
    return builder.as_markup()


def image_captcha_refresh_markup(chat_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Другая картинка", callback_data=ImageCaptchaKeyboard(chat_id=chat_id))
    return builder.as_markup()
