
DEFAULT_SETTING = {
    "antispam": {
        "name": "Анти-спам",
        "description": "Лулу защищает от спама шлюхоботов."
    },
    "antiflood": {
        "name": "Анти-флуд",
        "description": "Лулу защищает от флуда (большое кол-во сообщений от человека)."
    },
    "antiraid": {
        "name": "Анти-рейд",
        "description": "Лулу защищает от рейда (массовый вход или добавление участников) - лулу кикает рейдеров."
    },
    "welcome": {
        "name": "Приветствие",
        "description": "Лулу приветствует новых участников в чате."
    },
    "captcha": {
        "name": "Каптча",
        "description": "Лулу проверяет новых участников каптчей - пока она не пройдена, писать в чат нельзя."
    },
    "parting": {
        "name": "Прощание",
        "description": "Лулу прощается с участником что вышел из чата."
    },
    "moderation": {
        "name": "Модерация",
        "description": "Команды модерации для администраторов: мут, бан, кик, предупреждения."
    }
}

async def init_database():
    from database.loader import db
    from database.models.setting import Setting, SettingDescription
    from database.models.user import User
    from database.models.chat import Chat, ChatMember, WelcomedUser
    from database.models.statistic import MessageStatistic
    from database.models.captcha import Captcha
    from database.models.warn import Warn

    with db.atomic():
        db.create_tables(
            [
                User,
                Chat, ChatMember, WelcomedUser,
                Setting, SettingDescription,
                MessageStatistic,
                Captcha,
                Warn,
            ]
        )

    for i in DEFAULT_SETTING:
        setting = await SettingDescription.get_description(i)
        if not setting:
            await SettingDescription.add_description(
                setting_key=i,
                short_name=DEFAULT_SETTING[i]["name"],
                description=DEFAULT_SETTING[i]["description"]
            )
