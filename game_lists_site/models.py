import datetime as dt
from pathlib import Path

from appdirs import user_data_dir
from peewee import (
    AutoField,
    BigIntegerField,
    BooleanField,
    CompositeKey,
    DateField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

user_data_dir = Path(user_data_dir(
    appauthor='Niko Honue', appname='game_lists_site'))
user_data_dir.mkdir(exist_ok=True, parents=True)
database_path = user_data_dir / 'game_lists_site.db'
db = SqliteDatabase(database=database_path)


class BaseModel(Model):
    '''Base model for table in database'''
    class Meta:
        database = db


class SteamApp(BaseModel):
    id = BigIntegerField(primary_key=True)
    name = TextField()
    is_game = BooleanField(default=True)


class SteamProfile(BaseModel):
    id = BigIntegerField(primary_key=True)
    is_public = BooleanField(null=True)
    name = TextField(null=True)
    url = TextField(null=True)
    avatar_url = TextField(null=True)
    time_created = DateTimeField(null=True)
    last_update_time = DateTimeField(null=True)
    last_apps_update_time = DateTimeField(null=True)

    @property
    def __dict__(self):
        return {'id': self.id,
                'is_public': self.is_public,
                'name': self.name,
                'url': self.url,
                'avatar_url': self.avatar_url,
                'time_created': self.time_created.replace(tzinfo=dt.timezone.utc).timestamp(),
                'last_update_time': self.last_update_time.replace(tzinfo=dt.timezone.utc).timestamp() if self.last_update_time else None,
                'last_apps_update_time': self.last_apps_update_time.replace(tzinfo=dt.timezone.utc).timestamp() if self.last_apps_update_time else None}


class SteamProfileApp(BaseModel):
    steam_profile = ForeignKeyField(
        SteamProfile, on_delete='CASCADE', backref='steam_profile_apps')
    steam_app = ForeignKeyField(
        SteamApp, on_delete='CASCADE', backref='steam_profiles_app')
    playtime = IntegerField()

    class Meta:
        primary_key = CompositeKey('steam_profile', 'steam_app')


class GameStatistics(BaseModel):
    steam_app = ForeignKeyField(
        SteamApp, on_delete='CASCADE', backref='game_statistics', primary_key=True)
    total_playtime = IntegerField(null=True)
    mean_playtime = FloatField(null=True)
    median_playtime = FloatField(null=True)
    max_playtime = IntegerField(null=True)
    min_playtime = IntegerField(null=True)
    player_count = IntegerField(null=True)


class User(BaseModel):
    id = AutoField()
    username = TextField(unique=True)
    password = TextField()
    steam_profile = ForeignKeyField(
        SteamProfile, on_delete='CASCADE', backref='users')


class Game(BaseModel):
    id = AutoField()
    steam_app = ForeignKeyField(
        SteamApp, on_delete='CASCADE', backref='game_statistics', null=True,)


class Status(BaseModel):
    id = AutoField()
    name = TextField()


class UserGame(BaseModel):
    user = ForeignKeyField(
        User, on_delete='CASCADE', backref='users_game')
    game = ForeignKeyField(
        Game, on_delete='CASCADE', backref='user_games')
    score = IntegerField(null=True)
    status = ForeignKeyField(
        Status, on_delete='CASCADE', backref='user_games')
    predicted_score = FloatField(null=True)

    class Meta:
        primary_key = CompositeKey('user', 'game')


class UserGamePlaytime(BaseModel):
    id = AutoField()
    user_game = ForeignKeyField(
        User, on_delete='CASCADE', backref='user_game_playtimes',)
    is_steam_playtime = BooleanField()
    playtime = IntegerField()
    start_date = DateField()
    end_date = DateField()


models = BaseModel.__subclasses__()
db.create_tables(models)
