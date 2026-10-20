from aiogram import Router, types

from app.filters.lulu import LuluFilter
from app.filters.setting import CommandEnabled
from database.models.user import User
from database.models.chat import Chat
from database.models.statistic import MessageStatistic
from app.utils.emoji import get_emoji

router = Router()

def get_period_str(period: str):

    PERIOD = {
        "today": "за сегодня",
        "day": "за 24 часа",
        "week": "с начала недели",
        "month": "с начала месяца",
        "all": "за все время"
    }

    if isinstance(period, int):
        return f"{period} дней"

    return PERIOD[period]

def get_period(args: list | str):

    if isinstance(args, str): args = [args]
    for period in args:
        if period in ["сегодня"]: return "today"
        if period in ["день", "сутки"]: return "day"
        if period in ["неделя", "недели"]: return "week"
        if period in ["месяц", "месяца"]: return "month"
        if period in ["вся", "всё", "все"]: return "all"

    return "day"

def _parse_args(items: list):

    limit = None
    period = None

    for i in items:
        if isinstance(i, int) or str(i).isdigit(): limit = int(i)
        else: period = get_period(i)

    if limit is None: limit = 30
    if period is None: period = "day"

    return limit, period

@router.message(LuluFilter(command=['инф']))
async def test_cmd_info(message: types.Message):

    reply = message.reply_to_message

    chat = await Chat.get_chat(message.chat.id)
    user = await User.get_user(message.from_user.id)

    reply_text = ""
    if reply:
        reply_user = await User.get_user(reply.from_user.id)
        if reply_user:
            reply_text = (
                f"\n"
                f"Reply ID - {reply_user.user_id}\n"
                f"Reply UID - {reply_user.u_user_id}\n"
                f"Reply Фак - {reply_user.faculty}\n"

            )
        else: reply_text = f"Reply - Noname"

    text = (
        f"ID - {user.user_id}\n"
        f"UID - {user.u_user_id}\n"
        f"Фак - {user.faculty}\n"
        f"\nChat ID - {chat.chat_id}\n"
        f"Chat UID - {chat.u_chat_id}\n"
        f"{reply_text}"
    )

    await message.reply(text=text)





@router.message(LuluFilter(command=["стата", "статистика"]), CommandEnabled("стата"))
async def get_stats_handler(message: types.Message, lulu_args: list):
    if message.chat.type == "private":
        return

    _limit, period_filter = _parse_args(lulu_args)
    stats = await MessageStatistic.get_stats(message.chat.id, period=period_filter, limit=_limit)

    result = ""
    all_count = 0
    for place, i in enumerate(stats.get("stats")):
        user_id = i.user_id
        count = i.count
        all_count += count

        user = await User.get_name(user_id, True)
        place_emoji = {0: "clown", 1: "second_place", 2: "third_place"}.get(place)
        prefix = f"{get_emoji(place_emoji)} " if place_emoji else ""
        result += f"{prefix}{user} - {count}\n"

    period_text = get_period_str(period_filter)
    result_text = f"<blockquote>{result}</blockquote>" if len(result.splitlines()) <= 50 else f"<blockquote expandable>{result}</blockquote>"

    start_date = stats.get("start_date")
    end_date = stats.get("end_date")
    period_date_text = f"c {start_date} по {end_date}"

    result_text = (
        f"{get_emoji('stats_emoji')} <b>Статистика по общительным пользователям {period_text}</b>\n"
        f"<tg-spoiler>{period_date_text}</tg-spoiler>\n\n"
        f"{result_text}\n"
        f"Всего сообщений {all_count}"
    )

    return await message.reply(result_text)


