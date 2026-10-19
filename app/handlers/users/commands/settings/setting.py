from aiogram import Router, F
from html import escape

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.utils.captcha import CAPTCHA_PACKS, CUSTOM_CAPTCHA_PACK, load_custom_pack
from app.utils.emoji import get_emoji
from app.handlers.users.states import CaptchaPackInput, ProtectionInput
from app.config import Config
from app.filters.lulu import LuluFilter
from app.filters.is_chat_admin import IsChatAdmin
from database.models.setting import (
    ANTIFLOOD_PARAMETERS, CAPTCHA_IMPLEMENTED_LEVELS, CAPTCHA_LEVELS,
    Setting, SettingDescription, parse_antiflood_parameter,
)

from .keyboards.setting_keyboard import protection_menu, setting_menu, SettingKeyboard

router = Router()

@router.message(LuluFilter(command=["настройки", "настр", "защита", "з", "н"]), IsChatAdmin())
async def cmd_set_protect_handler(
    message: Message,
    config: Config,
    lulu_args: dict[list],
):
    args = lulu_args
    if len(args) != 2:

        await message.reply(
            text=f"Настройки чата «<b>{message.chat.title}</b>»",
            reply_markup=await setting_menu(message.from_user.id, message.chat.id))
        return

    protect, status_text = str(args[0]), str(args[1])
    protect = {"антиспам": "antispam", "антифлуд": "antiflood", "антирейд": "antiraid", "каптча": "captcha", "капча": "captcha"}.get(protect, protect)
    if protect not in {item["name"].casefold() for item in config.bot.protects}:
        return await message.answer("У Lulu нет такой защиты.")

    statuses = {"вкл": True, "включить": True, "выкл": False, "выключить": False}
    if status_text not in statuses:
        return await message.answer("Lulu не знает такой статус защиты.")

    status = statuses[status_text]
    if not await Setting.set_enabled(message.chat.id, protect, status):
        return await message.answer("Сначала задай текст - тогда настройка включится.")
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
    if data.setting_key == "captcha":
        level = await Setting.get_captcha_level(data.chat_id)
        text += f"\nУровень: {CAPTCHA_LEVELS[level].lower()}"
        if level == "basic":
            pack = await Setting.get_captcha_pack(data.chat_id)
            if pack == CUSTOM_CAPTCHA_PACK:
                pack_name = (await Setting.get_captcha_custom_pack(data.chat_id))["title"]
            else:
                pack_name = CAPTCHA_PACKS[pack][0]
            text += f"\nПак эмодзи: {escape(pack_name)}"

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

    elif data.action.startswith("lvl_") and data.setting_key == "captcha":
        level = data.action.removeprefix("lvl_")
        if level not in CAPTCHA_LEVELS:
            return await callback.answer("Неизвестный уровень каптчи.", show_alert=True)
        if level not in CAPTCHA_IMPLEMENTED_LEVELS:
            return await callback.answer("Этот уровень каптчи пока в разработке.", show_alert=True)
        await Setting.set_setting(data.chat_id, "captcha_level", level)
        await show_protection(callback.message, data)

    elif data.action == "pack_upload" and data.setting_key == "captcha":
        await state.set_state(CaptchaPackInput.waiting)
        await callback.message.reply(
            "Пришли ссылку на пак премиум-эмодзи (t.me/addemoji/...) или сообщение с любым эмодзи из него.\n"
            "Передумал - напиши «отмена»."
        )

    elif data.action.startswith("pack_") and data.setting_key == "captcha":
        pack = data.action.removeprefix("pack_")
        if pack == CUSTOM_CAPTCHA_PACK:
            if not await Setting.get_captcha_custom_pack(data.chat_id):
                return await callback.answer("Свой пак ещё не загружен.", show_alert=True)
        elif pack not in CAPTCHA_PACKS:
            return await callback.answer("Неизвестный пак.", show_alert=True)
        await Setting.set_setting(data.chat_id, "captcha_pack", pack)
        await show_protection(callback.message, data)

    elif data.action in {"s", "on", "off"}:
        await state.clear()
        if data.action != "s":
            if not await Setting.set_enabled(data.chat_id, data.setting_key, data.action == "on"):
                return await callback.answer("Сначала задай текст - тогда настройка включится.", show_alert=True)
        await show_protection(callback.message, data)
    else:
        return await callback.answer("Неизвестное действие.", show_alert=True)

    await callback.answer()


@router.message(CaptchaPackInput.waiting, IsChatAdmin())
async def captcha_pack_input_handler(message: Message, state: FSMContext):
    if (message.text or "").strip().casefold() in {"отмена", "отменить"}:
        await state.clear()
        return await message.reply("Загрузка пака отменена.")

    try:
        title, name, emojis = await load_custom_pack(message.bot, message)
    except ValueError as error:
        await state.clear()
        return await message.reply("Какая то ошибка, попробуйте позже.")
    except TelegramBadRequest:
        await state.clear()
        return await message.reply("Не нашла такой пак эмодзи.")

    if len(emojis) < 6:
        await state.clear()
        return await message.reply("Минимальное кол-во для пака: 6 эмодзи")

    await Setting.set_captcha_custom_pack(message.chat.id, name, title, emojis)
    await state.clear()
    await message.reply(f"Пак «<b>{escape(title)}</b>» загружен ({len(emojis)} эмодзи) и выбран для каптчи.")
    return