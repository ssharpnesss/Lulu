from peewee import SqliteDatabase, Model

db = SqliteDatabase("assets/database.db")

class BaseModel(Model):

    class Meta:
        database = db