
DEFAULT_SETTING = {
    "antispam": {
        "name": "Анти-спам",
        "description": "Защита от спама шлюхоботов."
    },
    "antiflood": {
        "name": "Анти-флуд",
        "description": "Защита от флуда (большое кол-во сообщений от человека)."
    },
    "welcome": {
        "name": "Приветствие",
        "description": "Приветствие новых участников в чате."
    },
    "parting": {
        "name": "Прощание",
        "description": "Прощание с участником что вышел из чата."
    }
}

async def init_database():
    from database.loader import db
    from database.models.setting import Setting, SettingDescription
    from database.models.user import User
    from database.models.chat import Chat, ChatMember
    from database.models.statistic import MessageStatistic
    from playhouse.migrate import SqliteMigrator, migrate

    with db.atomic():
        db.create_tables(
            [
                User,
                Chat, ChatMember,
                Setting, SettingDescription,
                MessageStatistic
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
