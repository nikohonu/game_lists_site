from datetime import date, datetime
from pathlib import Path
from string import ascii_uppercase

from appdirs import user_data_dir
from peewee import (BooleanField, CompositeKey, DateField, DateTimeField,
                    FloatField, ForeignKeyField, IntegerField, Model,
                    SqliteDatabase, TextField, BigIntegerField)

data_dir = Path(user_data_dir('game_lists_site', 'nikohonu'))
data_dir.mkdir(parents=True, exist_ok=True)
db = SqliteDatabase(data_dir / 'game_lists_site.db')


class BaseModel(Model):
    '''Base model for table in database'''
    class Meta:
        database = db


class User(BaseModel):
    steam_id = BigIntegerField()


models = BaseModel.__subclasses__()
db.create_tables(models)
