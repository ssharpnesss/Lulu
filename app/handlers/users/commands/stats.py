from aiogram import Router, types

from app.filters.lulu import LuluFilter
from database.models.user import User
from database.models.statistic import MessageStatistic

router = Router()

@router.message(LuluFilter(command=["стата", "статистика"]))
async def get_stats_handler(message: types.Message, lulu_args: list):
    if message.chat.type == "private":
        return

    period_filter = None

    stats = await MessageStatistic.get_stats(message.chat.id)

    result = ""
    for i in stats:
        user_id = i.user_id
        count = i.count

        user = await User.get_name(user_id, True,)

        result += f"{user} - {count}\n"

    return await message.reply(f"Статистика сообщений в чате\n\n{result}")


