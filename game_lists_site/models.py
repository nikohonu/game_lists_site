import json as jsonlib
from math import isnan
from pathlib import Path

from appdirs import user_data_dir
from peewee import (
    SQL,
    AutoField,
    BigIntegerField,
    BooleanField,
    CompositeKey,
    DateField,
    DateTimeField,
    Field,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    PostgresqlDatabase,
    TextField,
)


class JsonField(Field):
    field_type = "text"

    def db_value(self, value):
        if value:
            return jsonlib.dumps(value, allow_nan=False)
        else:
            return None

    def python_value(self, value):
        if value:
            return jsonlib.loads(value)
        else:
            return None


user_data_dir = Path(user_data_dir(appauthor="Niko Honu", appname="game_lists_site"))
user_data_dir.mkdir(exist_ok=True, parents=True)
db = PostgresqlDatabase("gls", user="gls", host="localhost", password="4277")


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
    cbr_update_time = DateTimeField(null=True)
    mbcf_update_time = DateTimeField(null=True)
    mobcf_update_time = DateTimeField(null=True)
    hr_update_time = DateTimeField(null=True)
    cbr = JsonField(null=True)
    similar_users = JsonField(null=True)
    mbcf = JsonField(null=True)
    mobcf = JsonField(null=True)
    hr = JsonField(null=True)

    normalization = JsonField(null=True)


class Game(BaseModel):
    id = BigIntegerField(primary_key=True)
    name = TextField(null=True)
    description = TextField(null=True)
    features = TextField(null=True)
    free_to_play = BooleanField(default=False)
    image_url = TextField(null=True)
    rating = IntegerField(null=True)
    release_date = DateField(null=True)

    last_update_time = DateTimeField(null=True)

    max_playtime = IntegerField(default=0)
    mean_playtime = FloatField(default=0)
    median_playtime = FloatField(default=0)
    min_playtime = IntegerField(default=0)
    player_count = IntegerField(null=True)
    playtime = IntegerField(default=0)
    score = FloatField(default=0)

    cbr = JsonField(null=True)
    hr = JsonField(null=True)
    mbcf = JsonField(null=True)

    normalization = JsonField(null=True)


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
    score = IntegerField(null=True)

    class Meta:
        constraints = [SQL("UNIQUE (user_id, game_id)")]
        # primary_key = CompositeKey("user", "game")


class System(BaseModel):
    key = TextField(primary_key=True)
    date_time = DateTimeField(null=True)
    date_time_value = DateTimeField(null=True)
    json = JsonField(null=True)


class GameCBR(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class UserCBR(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class BenchmarkUserCBR(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class UserSimilarity(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class BenchmarkUserSimilarity(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class UserMBCF(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class BenchmarkUserMBCF(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE", primary_key=True)
    data = JsonField(null=True)


class GameMBCF(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    data = TextField(null=True)


class GameStats(BaseModel):
    game = ForeignKeyField(Game, on_delete="CASCADE", primary_key=True)
    player_count = IntegerField(null=True)
    features = TextField(null=True)
    total_playtime = FloatField(default=0)
    mean_playtime = FloatField(default=0)
    median_playtime = FloatField(default=0)
    max_playtime = FloatField(default=0)
    min_playtime = FloatField(default=0)
    rating = FloatField(default=0)
    last_update_time = DateTimeField(null=True)


class Parameters(BaseModel):
    name = TextField(primary_key=True)
    last = JsonField(null=True)
    best = JsonField(null=True)


models = BaseModel.__subclasses__()
db.create_tables(models)
