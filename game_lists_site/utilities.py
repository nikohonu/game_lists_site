import datetime as dt

import numpy as np
import scipy.stats as stats
from sklearn import preprocessing

import game_lists_site.utils.steam as steam
from game_lists_site.models import (
    Developer,
    Game,
    GameDeveloper,
    GameGenre,
    GameTag,
    Genre,
    Parameters,
    Tag,
    UserGame,
)

not_game_ids = [
    202090,
    205790,
    214850,
    217490,
    225140,
    226320,
    239450,
    250820,
    285030,
    310380,
    323370,
    36700,
    388080,
    404790,
    41010,
    413850,
    413851,
    413852,
    413853,
    413854,
    413855,
    413856,
    413857,
    413858,
    413859,
    431960,
    458250,
    458260,
    458270,
    458280,
    458300,
    458310,
    458320,
    497810,
    497811,
    497812,
    497813,
    585280,
    585281,
    585282,
    585283,
    607380,
    623990,
    700580,
]

class ParametersManager:
    def __init__(self, name, current_parameters, best) -> None:
        self.p, _ = Parameters.get_or_create(name=name)
        self.cp = current_parameters
        if not self.p.best:
            self.best = best
        for key, value in self.p.best.items():
            if key not in self.cp:
                self.cp[key] = value

    def is_diff_last_current(self):
        diff = False
        if not self.p.last:
            return True
        for key, value in self.p.last.items():
            if self.cp[key] != value:
                diff = True
        return diff

    def __getitem__(self, value):
        return self.cp[value]

    def set_best_parameter(self, best: dict):
        self.p.best = best

    def __del__(self):
        self.p.last = self.cp
        self.p.save()


def merge_dicts(dicts: list):
    result = {}
    for d in dicts:
        for v in d:
            if v in result:
                result[v] += d[v]
            else:
                result[v] = d[v]
    result = {
        key: value
        for key, value in sorted(result.items(), key=lambda item: item[1], reverse=True)
    }
    return result


def normalize_dict(dict_data: dict, coef: float = 1):
    values = list(dict_data.values())
    values = preprocessing.normalize([values])[0] * coef
    return {k: v for k, v in zip(dict_data, values)}


def days_delta(date_time):
    if not date_time:
        return float("inf")
    return (dt.datetime.now() - date_time).days


def slice_dict(d, start, end):
    if d:
        return dict(list(d.items())[start:end])
    else:
        return {}


developers_fix = {
    "FromSoftware, Inc.": "FromSoftware",
    "FromSoftware, Inc": "FromSoftware",
    "FromSoftware Inc.": "FromSoftware",
    "Aspyr(Linux)": "Aspyr",
    "Aspyr(Mac)": "Aspyr",
    "Aspyr (Mac, Linux, & Windows Update)": "Aspyr",
    "Aspyr (Mac)": "Aspyr",
    "Feral Interactive (Mac/Linux)": "Feral Interactive",
    "Feral Interactive (Mac)": "Feral Interactive",
    "Feral Interactive (Linux)": "Feral Interactive",
    "Feral Interactive": "Feral Interactive",
}


def update_game(game_id: int):
    game = Game.get_or_none(Game.id == game_id)
    if game == None or days_delta(game.last_update_time) > 30:
        print("update game")
        if game_id in not_game_ids:
            return None
        data = steam.get_app_details(game_id)
        if not data:
            return None
        if not game:
            game, _ = Game.get_or_create(id=data["steam_appid"])
        game.name = data["name"]
        game.description = data.get("about_the_game", "")
        # get release date or none
        if data["release_date"]["date"]:
            try:
                game.release_date = dt.datetime.strptime(
                    data["release_date"]["date"], "%d %b, %Y"
                ).date()
            except:
                game.release_date = None
        game.image_url = data["header_image"]
        # clear
        q = GameDeveloper.delete().where(GameDeveloper.game == game)
        q.execute()
        q = GameGenre.delete().where(GameGenre.game == game)
        q.execute()
        q = GameTag.delete().where(GameTag.game == game)
        q.execute()
        for developer_name in data.get("developers", []):
            if developer_name in developers_fix:
                developer_name = developers_fix[developer_name]
            developer, _ = Developer.get_or_create(name=developer_name)
            GameDeveloper.get_or_create(game=game, developer=developer)
        genre_blacklist = []
        genre_blacklist.extend(range(50, 60 + 1))
        genre_blacklist.extend(range(80, 85 + 1))
        for genre_dict in data.get("genres", []):
            genre, _ = Genre.get_or_create(
                id=genre_dict["id"], name=genre_dict["description"]
            )
            if genre.id in genre_blacklist:
                game.delete_instance()
                return None
            if genre.id == 37:
                game.free_to_play = True
            GameGenre.get_or_create(game=game, genre=genre)
        for tag_name in steam.get_app_tags(game.id):
            tag, _ = Tag.get_or_create(name=tag_name)
            GameTag.get_or_create(game=game, tag=tag)
        game.rating = steam.get_app_rating(game.id)
        game.last_update_time = dt.datetime.now()
        # save
        game.save()
    if game:
        return game
    else:
        return None


def update_game_stats(game):
    features = []
    features += [
        developer.name.replace(" ", "")
        for developer in Developer.select(Developer.name)
        .join(GameDeveloper)
        .where(GameDeveloper.game == game)
    ]
    features += [
        genre.name.replace(" ", "")
        for genre in Genre.select(Genre.name)
        .join(GameGenre)
        .where(GameGenre.game == game)
    ]
    features += [
        tag.name.replace(" ", "")
        for tag in Tag.select(Tag.name).join(GameTag).where(GameTag.game == game)
    ]
    game.features = " ".join(features)
    # update stats based on playtime
    users_game = UserGame.select(UserGame.id, UserGame.playtime).where(
        (UserGame.game == game) & (UserGame.playtime > 0)
    )
    game.player_count = users_game.count()
    playtimes = np.array([ug.playtime for ug in users_game])
    game.playtime = 0
    game.mean_playtime = 0
    game.median_playtime = 0
    game.max_playtime = 0
    game.min_playtime = 0
    if len(playtimes) > 0:
        game.playtime = np.sum(playtimes)
        game.mean_playtime = np.mean(playtimes)
        game.median_playtime = np.median(playtimes)
        game.max_playtime = np.max(playtimes)
        game.min_playtime = np.min(playtimes)
    game.save()


def update_game_score_stats(game):
    users_game = UserGame.select(UserGame.score).where(
        (UserGame.game == game) & (UserGame.score > 0)
    )
    scores = np.array([ug.score for ug in users_game])
    if len(scores) > 2:
        game.score = np.mean(scores)
    game.save()


def get_normalized_playtimes(min_player_count, zscore):
    games = [
        g for g in Game.select(Game.id).where(Game.player_count >= min_player_count)
    ]
    users_games = UserGame.select(UserGame.playtime, UserGame.user).where(
        UserGame.playtime > 0
    )
    result = {}
    for game in games:
        users_game = users_games.where(UserGame.game == game)
        playtimes = [user_game.playtime for user_game in users_game]
        if zscore:
            playtimes = stats.zscore(playtimes)
        else:
            playtimes = preprocessing.normalize([playtimes])[0]
        result[game.id] = {
            ug.user.id: playtime for ug, playtime in zip(users_game, playtimes)
        }
    return result


def get_game_vecs(min_player_count, min_game_count):
    normalized_playtimes = get_normalized_playtimes(min_player_count, False)
    games = list(normalized_playtimes.keys())
    users = {}
    for game in normalized_playtimes.keys():
        for u in normalized_playtimes[game].keys():
            if u in users:
                users[u] += 1
            else:
                users[u] = 1
    users = [u for u, game_count in users.items() if game_count >= min_game_count]
    game_vecs = []
    for game in games:
        game_vec = []
        for u in users:
            value = normalized_playtimes[game].get(u)
            game_vec.append(value if value else 0)
        game_vecs.append(game_vec)
    game_vecs = np.array(game_vecs, dtype=np.float32)
    return games, users, game_vecs


def get_readable_result_for_games(d: dict, size: int):
    d = slice_dict(d, 1, size + 1)
    return {Game.get_by_id(int(game_id)): value for game_id, value in d.items()}
