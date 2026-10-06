from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

from database.models.setting import ANTIFLOOD_PARAMETERS, Setting, SettingDescription

class SettingKeyboard(CallbackData, prefix="setting"):
    action: str
    setting_key: str
    user_id: int
    chat_id: int

    # в дальнейшем лучше сделать через бд

async def get_only_setting_menu(setting: str, user_id: int, chat_id: int, button_text: str = None, button_emoji: str = None):
    builder = InlineKeyboardBuilder()

    item = await SettingDescription.get_description(setting)
    if not item: return None

    _setting_status = await Setting.is_enabled(chat_id, item.setting_key)
    _status = "SUCCESS" if _setting_status else "DANGER"
    button = InlineKeyboardButton(
        text=item.short_name if not button_text else button_text.replace("[name]", item.short_name.lower()),
        style=_status,
        icon_custom_emoji_id=item.button_emoji if not button_emoji else button_emoji,
        callback_data=SettingKeyboard(
            action="s",
            setting_key=item.setting_key,
            user_id=user_id,
            chat_id=chat_id
        ).pack()
    )
    builder.row(button)

    return builder.as_markup()


async def protection_menu(setting_key: str, user_id: int, chat_id: int):
    builder = InlineKeyboardBuilder()
    enabled = await Setting.is_enabled(chat_id, setting_key)

    def button(text: str, action: str, emj_id: str | None = None, style: str = "primary"):
        return InlineKeyboardButton(text=text, icon_custom_emoji_id=emj_id, style=style, callback_data=SettingKeyboard(
            action=action, setting_key=setting_key, user_id=user_id, chat_id=chat_id,
        ).pack())

    builder.row(
        button(text="Вкл" if enabled else "Вкл", action="on", style="success" if enabled else "danger"), 
        button(text="Выкл" if enabled else "Выкл", style="danger" if enabled else "success", action="off")
    )
    if setting_key == "antiflood":
        values = await Setting.get_antiflood_parameters(chat_id)
        for parameter, (label, _, _) in ANTIFLOOD_PARAMETERS.items():
            builder.row(button(f"{label}: {values[parameter]:g}", parameter))
            
    builder.row(button("Назад", "back"))
    return builder.as_markup()

async def setting_menu(user_id: int, chat_id: int):

    builder = InlineKeyboardBuilder()
    buttons = []

    descriptions = await SettingDescription.get_all_descriptions()
    for item in descriptions:
        _setting_status = await Setting.is_enabled(chat_id, item.setting_key)
        _status = "SUCCESS" if _setting_status else "DANGER"
        button = InlineKeyboardButton(
            text=item.short_name,
            style=_status,
            icon_custom_emoji_id=item.button_emoji,
            callback_data=SettingKeyboard(
                action="s",
                setting_key=item.setting_key,
                user_id=user_id,
                chat_id=chat_id
            ).pack()
        )
        buttons.append(button)
    
    builder.row(*buttons).adjust(2)    

    return builder.as_markup()

