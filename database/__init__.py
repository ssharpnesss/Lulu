def init_database():
    from database.loader import db
    from database.models.protects import Protects
    from database.models.user import User
    from database.models.chats import Chats
    from playhouse.migrate import SqliteMigrator, migrate

    with db.atomic():
        if db.table_exists("chats"):
            columns = {column.name for column in db.get_columns("chats")}
            if "is_deleted" not in columns:
                migrate(SqliteMigrator(db).add_column(
                    "chats", "is_deleted", Chats.is_deleted
                ))
        db.create_tables(
            [
                User,
                Chats,
                Protects,
            ]
        )
