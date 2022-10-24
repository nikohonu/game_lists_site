import datetime as dt

import numpy as np
import scipy.stats as stats
from sklearn import preprocessing
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import game_lists_site.utils.steam as steam
from game_lists_site.models import (
    Developer,
    Game,
    GameDeveloper,
    GameGenre,
    GameTag,
    Genre,
    Parameters,
    System,
    Tag,
    UserGame,
    db,
)


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
        print("Update game")
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
    return True


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


def update_cbr_for_game(min_player_count=-1):
    parameters, _ = Parameters.get_or_create(name="cbr_for_game")
    if not parameters.best:
        parameters.best = {"min_player_count": 10}
    if not parameters.last:
        parameters.last = {}
    if min_player_count == -1:
        min_player_count = parameters.best["min_player_count"]
    last_min_player_count = parameters.last.get("min_player_count")
    system, _ = System.get_or_create(key="cbr_for_game")
    if days_delta(system.date_time) > 30 or last_min_player_count != min_player_count:
        print("update cbr for game")
        Game.update({Game.cbr: None}).execute()
        games = Game.select(Game.id, Game.features).where(
            (Game.features != None)
            & (Game.player_count > min_player_count)
            & (Game.rating >= 7)
        )
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform([g.features for g in games])
        csr = cosine_similarity(X, X)
        result = {}
        for game_a, row in zip(games, csr):
            game_a.cbr = dict(
                sorted(
                    [(game_b.id, value) for game_b, value in zip(games, row)],
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
        Game.bulk_update(games, [Game.cbr])
        system.date_time = dt.datetime.now()
        system.save()
        parameters.last = {"min_player_count": min_player_count}
        parameters.save()


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


def update_mbcf_for_games(min_player_count=-1, min_game_count=-1):
    parameters, _ = Parameters.get_or_create(name="mbcf_for_game")
    if not parameters.best:
        parameters.best = {"min_player_count": 10, "min_game_count": 10}
    if not parameters.last:
        parameters.last = {}
    if min_player_count == -1:
        min_player_count = parameters.best["min_player_count"]
    if min_game_count == -1:
        min_game_count = parameters.best["min_game_count"]
    last_min_player_count = parameters.last.get("min_player_count")
    last_min_game_count = parameters.last.get("min_game_count")
    system, _ = System.get_or_create(key="mbcf_for_game")
    if (
        days_delta(system.date_time) > 30
        or last_min_player_count != min_player_count
        or last_min_game_count != min_game_count
    ):
        print("update mbcf for game")
        Game.update({Game.mbcf: None}).execute()
        game_ids, _, game_vecs = get_game_vecs(min_player_count, min_game_count)
        games = [Game.get_by_id(game_id) for game_id in game_ids]
        game_vecs = np.corrcoef(game_vecs)
        for game_a, row in zip(games, game_vecs):
            game_a.mbcf = dict(
                sorted(
                    [(game_id_b, value) for game_id_b, value in zip(game_ids, row)],
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
        Game.bulk_update(games, [Game.mbcf])
        system.date_time = dt.datetime.now()
        system.save()
        parameters.last = {
            "min_player_count": min_player_count,
            "min_game_count": min_game_count,
        }
        parameters.save()


def update_hr_for_games(cbr_coef=-1, mbcf_coef=-1):
    parameters, _ = Parameters.get_or_create(name="hr_for_game")
    if not parameters.best:
        parameters.best = {"cbr_coef": 0.75, "mbcf_coef": 0.25}
    if not parameters.last:
        parameters.last = {}
    if cbr_coef == -1:
        cbr_coef = parameters.best["cbr_coef"]
    if mbcf_coef == -1:
        mbcf_coef = parameters.best["mbcf_coef"]
    last_cbr_coef = parameters.last.get("cbr_coef")
    last_mbcf_coef = parameters.last.get("mbcf_coef")
    system, _ = System.get_or_create(key="hr_for_game")
    if (
        days_delta(system.date_time) > 30
        or last_cbr_coef != cbr_coef
        or last_mbcf_coef != mbcf_coef
    ):
        print("update hr for game")
        Game.update({Game.hr: None}).execute()
        games = Game.select(Game.id, Game.cbr, Game.mbcf)
        for game in games:
            cbr_result = game.cbr
            mbcf_result = game.mbcf
            game.hr = merge_dicts(
                [
                    normalize_dict(cbr_result, cbr_coef) if cbr_result else [],
                    normalize_dict(mbcf_result, mbcf_coef) if mbcf_result else [],
                ]
            )
            if not game.hr:
                game.hr = None
        Game.bulk_update(games, [Game.hr])
        system.date_time = dt.datetime.now()
        system.save()
        parameters.last = {
            "cbr_coef": cbr_coef,
            "mbcf_coef": mbcf_coef,
        }
        parameters.save()
