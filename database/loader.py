from pathlib import Path

from peewee import SqliteDatabase, Model

db = SqliteDatabase(
    "assets/database.db",
    pragmas={"journal_mode": "wal", "synchronous": "normal"},
    check_same_thread=False,
)

class BaseModel(Model):

    class Meta:
        database = db
