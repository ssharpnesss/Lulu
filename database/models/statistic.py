from peewee import *
from aiogram import types

from database.loader import BaseModel
from app.utils.time import get_now
from datetime import datetime, timedelta, time

class MessageStatistic(BaseModel):

    chat_id = BigIntegerField()
    user_id = BigIntegerField()
    message_id = BigIntegerField()

    file_id = CharField(null=True)
    file_type = CharField(null=True)
    text = TextField(null=True)

    reply_to_message_id = BigIntegerField(null=True)

    created_at = DateTimeField(default=get_now)

    class Meta:
        table_name = "message_statistics"

    @classmethod
    async def add_message(cls, message: types.Message):
        if message.chat.type == "private": return

         # думаю в дальнейшем сделать что то типо кэша и сначало сохранять в кэш
         # (мб редис) и потом закидывать в бд что бы не нагружать частыми запросами

        chat = message.chat
        user = message.from_user

        file_id = None
        file_type = None
        text = None
        reply_to_message_id = None

        if message.text:  text = message.text
        if message.caption: text = message.caption

        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "photo"

        if message.video:
            file_id = message.video.file_id
            file_type = "video"

        if message.audio:
            file_id = message.audio.file_id
            file_type = "audio"

        if message.document:
            file_id = message.document.file_id
            file_type = "document"

        if message.animation:
            file_id = message.animation.file_id
            file_type = "animation"

        if message.voice:
            file_id = message.voice.file_id
            file_type = "voice"

        if message.video_note:
            file_id = message.video_note.file_id
            file_type = "video_note"

        if message.sticker:
            file_id = message.sticker.file_id
            file_type = "sticker"

        if message.dice:
            file_id = message.dice.value
            file_type = f"dice_{message.dice.emoji}"

        if message.contact:
            file_id = f"{message.contact.user_id}__{message.contact.full_name}"
            file_type = f"contact_{message.contact.phone_number}" if message.contact.phone_number else f"contact_0"

        if message.location:
            file_id = f"{message.location.latitude}__{message.location.longitude}"
            file_type = f"location"

        if message.venue:
            file_id = f"{message.venue.location.latitude}__{message.venue.location.longitude}__{message.venue.address}"
            file_type = f"venue_{message.venue.title}"

        if message.poll:
            file_id = message.poll.question
            file_type = f"poll"

        if message.checklist:
            file_id = message.checklist.title
            file_type = f"checklist"
            text = ""

            for i in message.checklist.tasks:
                text += f"{i.id} | {i.text}\n"

        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id

        cls.create(
            chat_id=chat.id,
            user_id=user.id,
            message_id=message.message_id,
            file_id=file_id,
            file_type=file_type,
            text=text,
            reply_to_message_id=reply_to_message_id
        )

    @classmethod
    async def get_stats(cls, chat_id: int, period: str = "day", limit: int = 30):

        items = cls.select(cls.user_id, fn.COUNT(cls.id).alias("count")).group_by(cls.user_id).where(cls.chat_id==chat_id)

        _start_date = None
        _end_date = get_now()

        if period == "today":
            _start_date = datetime.combine(get_now().date(), time.min)
            items = items.where(cls.created_at >= _start_date)

        if period == "day":
            _start_date = _end_date - timedelta(days=1)
            items = items.where(cls.created_at >= _start_date)

        if period == "week":
            _start_date = datetime.combine(_end_date - timedelta(days=_end_date.weekday()), time.min)
            items = items.where(cls.created_at >= _start_date)

        if period == "month":
            _start_date = datetime.combine(_end_date.replace(day=1), time.min)
            items = items.where(cls.created_at >= _start_date)

        if period == "all":
            first_ = cls.select(cls.created_at).where(cls.chat_id==chat_id).order_by(cls.created_at.asc()).first()
            if first_ is None: _start_date = _end_date
            else: _start_date = first_.created_at
            items = items

        if isinstance(period, int):
            _start_date = _end_date - timedelta(days=period)
            items = items.where(cls.created_at >= _start_date)

        
        data = {
            "period": period,
            "start_date": _start_date.strftime("%Y/%m/%d %H:%M"),
            "end_date": _end_date.strftime("%Y%m/%d %H:%M"),
            "limit": limit,
            "stats": items.order_by(fn.COUNT(cls.id).desc()).limit(limit),
        }

        return data 

        




