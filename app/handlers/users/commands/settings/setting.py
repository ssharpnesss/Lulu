from aiogram import Router, F
from aiogram.enums import ChatType
from html import escape

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.utils.emoji import get_emoji
from app.handlers.users.states import ProtectionInput
from app.config import Config
from app.filters.lulu import LuluFilter
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import (
    ANTIFLOOD_PARAMETERS, Setting, SettingDescription, parse_antiflood_parameter,
)

from .keyboards.setting_keyboard import protection_menu, setting_menu, SettingKeyboard

router = Router()

@router.message(LuluFilter(command=["настройки", "настр", "защита", "з", "н"]), IsChatAdmin())
async def cmd_set_protect_handler(
    message: Message,
    config: Config,
    lulu_args: dict[list],
):
    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return await message.answer("Lulu подсказывает:\nТакие команды используются только в чатах!") # можно будет брать где чел админ/владелец и открывать в лс

    args = lulu_args
    if len(args) != 2:

        await message.reply(
            text=f"Настройки чата «<b>{message.chat.title}</b>»",
            reply_markup=await setting_menu(message.from_user.id, message.chat.id))
        return

    protect, status_text = str(args[0]), str(args[1])
    protect = {"антиспам": "antispam", "антифлуд": "antiflood"}.get(protect, protect)
    if protect not in {item["name"].casefold() for item in config.bot.protects}:
        return await message.answer("У Lulu нет такой защиты.")

    statuses = {"вкл": True, "включить": True, "выкл": False, "выключить": False}
    if status_text not in statuses:
        return await message.answer("Lulu не знает такой статус защиты.")

    status = statuses[status_text]
    await Setting.set_setting(message.chat.id, protect, "on" if status else "off")
    await message.answer(f"Я {'включила' if status else 'выключила'} {protect}")

async def show_protection(message: Message, data: SettingKeyboard):
    description = await SettingDescription.get_description(data.setting_key)
    if not description:
        return

    enabled = await Setting.is_enabled(data.chat_id, data.setting_key)
    text = (
        f"<b>{description.short_name}</b>\n"
        f"{description.description}\n\n"
        f"{get_emoji('on_status') if enabled else get_emoji('off_status')} Статус: {'включено' if enabled else 'выключено'}"
    )
    markup = await protection_menu(data.setting_key, data.user_id, data.chat_id)
    if message.text != text or message.reply_markup != markup:
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as error:
            print(error)
            raise

@router.callback_query(SettingKeyboard.filter(), IsChatAdmin())
async def chat_settings_check_handler(callback: CallbackQuery, callback_data: SettingKeyboard, state: FSMContext,):
    data = callback_data

    if data.user_id != callback.from_user.id:
        return await callback.answer("Не трогай чужое.", show_alert=True)

    if data.action == "back":
        await state.clear()
        await callback.message.edit_text(
            f"Настройки чата «<b>{escape(callback.message.chat.title or '')}</b>»",
            reply_markup=await setting_menu(data.user_id, data.chat_id),
        )
        return await callback.answer()

    if data.action in ANTIFLOOD_PARAMETERS and data.setting_key == "antiflood":
        label, _, maximum = ANTIFLOOD_PARAMETERS[data.action]
        await state.set_state(ProtectionInput.value)

        # aleks sosi bibu

    elif data.action in {"s", "on", "off"}:
        await state.clear()
        if data.action != "s":
            await Setting.set_setting(data.chat_id, data.setting_key, data.action)
        await show_protection(callback.message, data)
    else:
        return await callback.answer("Неизвестное действие.", show_alert=True)
