from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.captcha import CUSTOM_EMOJI_BUTTON_TEXT
from database.models.captcha import Captcha


class CaptchaKeyboard(CallbackData, prefix="captcha"):
    user_id: int
    index: int


def captcha_markup(captcha: Captcha):
    builder = InlineKeyboardBuilder()
    for index, (fallback, emoji_id) in enumerate(captcha.option_list):
        builder.button(
            # премиум-эмодзи показываем иконкой без текста, чтобы fallback не подсказывал ответ
            text=CUSTOM_EMOJI_BUTTON_TEXT if emoji_id else fallback,
            icon_custom_emoji_id=emoji_id,
            callback_data=CaptchaKeyboard(user_id=captcha.user_id, index=index),
        )
    builder.adjust(3)
    return builder.as_markup()
