from aiogram import Router, F, types

router = Router()

STAT_TEXT_FILTER = F.text | F.caption 
STAT_MEDIA_FILTER = F.photo | F.video | F.audio | F.document | F.sticker | F.animation
STAT_OTHER_FILTER = F.venue | F.voice | F.video_note | F.location | F.contact | F.poll | F.dice | F.checklist

ALL_STAT_FILTER = STAT_TEXT_FILTER | STAT_MEDIA_FILTER | STAT_OTHER_FILTER

@router.message(ALL_STAT_FILTER)
async def stat_getter_handler(message: types.Message):
    pass