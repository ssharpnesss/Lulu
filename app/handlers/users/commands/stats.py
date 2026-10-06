from aiogram import Router, types

from app.filters.lulu import LuluFilter
from database.models.user import User
from database.models.statistic import MessageStatistic
from app.utils.emoji import get_emoji as EMOJI

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



@router.message(LuluFilter(command=["стата", "статистика"]))
async def get_stats_handler(message: types.Message, lulu_args: list):
    if message.chat.type == "private":
        return

    _limit, period_filter = _parse_args(lulu_args)
    stats = await MessageStatistic.get_stats(message.chat.id, period=period_filter, limit=_limit)

    result = ""
    all_count = 0
    for i in stats.get("stats"):
        user_id = i.user_id
        count = i.count
        all_count += count

        user = await User.get_name(user_id, True,)
        result += f"{user} - {count}\n"

    period_text = get_period_str(period_filter)
    result_text = f"<blockquote>{result}</blockquote>" if len(result.splitlines()) <= 50 else f"<blockquote expandable>{result}</blockquote>"

    start_date = stats.get("start_date")
    end_date = stats.get("end_date")
    period_date_text = f"c {start_date} по {end_date}"

    result_text = (
        f"{EMOJI('stats_emoji')} <b>Статистика по общительным пользователям {period_text}</b>\n"
        f"<tg-spoiler>{period_date_text}</tg-spoiler>\n\n"
        f"{result_text}\n"
        f"Всего сообщений {all_count}"
    )

    return await message.reply(result_text)


