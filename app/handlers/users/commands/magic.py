from aiogram import Router, types

from app.filters.lulu import LuluFilter
from app.filters.setting import CommandEnabled
from database.models.user import User
from database.models.statistic import MessageStatistic
from app.utils.emoji import get_emoji

router = Router()

@router.message(LuluFilter(command=['магия', 'магия внехогвартса', 'хогвартс']))
async def cmd_magic_handler(message: types.Message):
    if message.reply_to_message.sticker:
        sticker_id = message.reply_to_message.sticker.file_id
        