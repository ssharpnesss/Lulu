def init_database():
    from database.loader import db
    from database.models.protects import Protects
    from database.models.user import User
    from database.models.chats import Chats
    from playhouse.migrate import SqliteMigrator, migrate

    with db.atomic():
        if db.table_exists("chats"):
            columns = {column.name for column in db.get_columns("chats")}
            for name in ("is_deleted", "welcome_template"):
                if name not in columns:
                    migrate(SqliteMigrator(db).add_column(
                        "chats", name, getattr(Chats, name)
                    ))
        db.create_tables(
            [
                User,
                Chats,
                Protects,
            ]
        )
