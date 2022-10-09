from pathlib import Path

from appdirs import user_data_dir
from peewee import (
    AutoField,
    BigIntegerField,
    CompositeKey,
    DateField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    PostgresqlDatabase,
    TextField,
)

user_data_dir = Path(user_data_dir(appauthor="Niko Honu", appname="game_lists_site"))
user_data_dir.mkdir(exist_ok=True, parents=True)
db = PostgresqlDatabase(
    "game_lists_site", user="gls", password="4277", host="localhost"
)


class BaseModel(Model):
    """Base model for table in database"""

    class Meta:
        database = db


class User(BaseModel):
    id = BigIntegerField(primary_key=True)
    username = TextField(unique=True)
    password = TextField()
    avatar_url = TextField(null=True)
    profile_url = TextField(null=True)
    last_update_time = DateTimeField(null=True)
    last_games_update_time = DateTimeField(null=True)
    last_cbr_update_time = DateTimeField(null=True)


class Game(BaseModel):
    id = BigIntegerField(primary_key=True)
    name = TextField()
    description = TextField(null=True)
    release_date = DateField(null=True)
    image_url = TextField(null=True)
    last_update_time = DateTimeField(null=True)
    rating = IntegerField(null=True)


class Developer(BaseModel):
    id = AutoField()
    name = TextField()


class GameDeveloper(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE")
    developer = ForeignKeyField(Developer, on_delete="CASCADE")

    class Meta:
        primary_key = CompositeKey("game", "developer")


class Genre(BaseModel):
    id = IntegerField(primary_key=True)
    name = TextField()


class GameGenre(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE")
    genre = ForeignKeyField(Genre, on_delete="CASCADE")

    class Meta:
        primary_key = CompositeKey("game", "genre")


class Tag(BaseModel):
    id = AutoField()
    name = TextField()


class GameTag(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE")
    tag = ForeignKeyField(Tag, on_delete="CASCADE")

    class Meta:
        primary_key = CompositeKey("game", "tag")


class UserGame(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE")
    game = ForeignKeyField(Game, on_delete="CASCADE")
    last_played = DateTimeField(null=True)
    playtime = IntegerField(default=0)
    normalized_playtime = FloatField(default=0)
    score = IntegerField(null=True)

    class Meta:
        primary_key = CompositeKey("user", "game")


class System(BaseModel):
    key = TextField(primary_key=True)
    date_time_value = DateTimeField(null=True)


class GameCBR(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class UserCBR(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class UserMBCF(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class GameMBCF(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class GameStats(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    player_count = IntegerField(null=True)
    features = TextField(null=True)
    last_update_time = DateTimeField(null=True)


models = BaseModel.__subclasses__()
db.create_tables(models)
