
from game_lists_site.models import (
    User,
    UserCBR,
    Game,
    UserGame,
    System,
    GameStats,
    GameDeveloper,
    GameGenre,
    GameTag,
    GameCBR,
)
import datetime as dt
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
from operator import itemgetter
from game_lists_site.models import db


def days_delta(datetime):
    if not datetime:
        return float("inf")
    return (dt.datetime.now() - datetime).days

# def get_game_stats(game: Game):
#     game_stats = GameStats.get_or_none(GameStats.game == game)
#     if not game_stats or days_delta(game_stats.last_update_time) >= 7:
#         game_stats, _ = GameStats.get_or_create(game=game)
#         # features
#         features = []
#         features += [
#             game_developer.developer.name.replace(" ", "")
#             for game_developer in GameDeveloper.select().where(
#                 GameDeveloper.game == game
#             )
#         ]
#         features += [
#             game_genre.genre.name.replace(" ", "")
#             for game_genre in GameGenre.select().where(GameGenre.game == game)
#         ]
#         features += [
#             game_tag.tag.name.replace(" ", "")
#             for game_tag in GameTag.select().where(GameTag.game == game)
#         ]
#         # features end
#         users_game = UserGame.select(UserGame.playtime, UserGame.score).where(UserGame.game == game)
#         game_stats.player_count = len(
#             users_game.where(UserGame.playtime > 0)
#         )
#         game_stats.features = " ".join(features)
#         playtimes = np.array([ug.playtime for ug in users_game.where(UserGame.playtime > 0)])
#         scores = np.array([ug.score for ug in users_game.where(UserGame.score > 0)])
#         if len(playtimes) > 0:
#             game_stats.total_playtime = np.sum(playtimes)
#             game_stats.mean_playtime = np.mean(playtimes)
#             game_stats.median_playtime = np.median(playtimes)
#             game_stats.max_playtime = np.max(playtimes)
#             game_stats.min_playtime = np.min(playtimes)
#             if len(scores) > 2:
#                 game_stats.rating = np.mean(scores)
#             else:
#                 game_stats.rating = 0
#         game_stats.last_update_time = dt.datetime.now()
#         game_stats.save()
#     return game_stats

def get_game_stats(game: Game):
    game_stats = GameStats.get_or_none(GameStats.game == game)
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        # features
        features = []
        features += [
            game_developer.developer.name.replace(" ", "")
            for game_developer in GameDeveloper.select(GameDeveloper.developer).where(
                GameDeveloper.game == game
            )
        ]
        features += [
            game_genre.genre.name.replace(" ", "")
            for game_genre in GameGenre.select(GameGenre.genre).where(GameGenre.game == game)
        ]
        features += [
            game_tag.tag.name.replace(" ", "")
            for game_tag in GameTag.select(GameTag.tag).where(GameTag.game == game)
        ]
        game_stats.features = " ".join(features)
        # features end
        users_game = UserGame.select(UserGame.playtime, UserGame.score).where(UserGame.game == game)
        users_game_with_playtime = users_game.where(UserGame.playtime > 0)
        users_game_with_score = users_game.where(UserGame.score > 0)
        game_stats.player_count = users_game_with_playtime.count()
        playtimes = np.array(
            [ug.playtime for ug in users_game_with_playtime]
        )
        scores = np.array([ug.score for ug in users_game_with_score])
        if len(playtimes) > 0:
            game_stats.total_playtime = np.sum(playtimes)
            game_stats.mean_playtime = np.mean(playtimes)
            game_stats.median_playtime = np.median(playtimes)
            game_stats.max_playtime = np.max(playtimes)
            game_stats.min_playtime = np.min(playtimes)
            if len(scores) > 2:
                game_stats.rating = np.mean(scores)
            else:
                game_stats.rating = 0
        game_stats.last_update_time = dt.datetime.now()
        game_stats.save()
    return game_stats

# def get_cbr_for_game(target_game, result_count=9):
#     system, _ = System.get_or_create(key="GameCBR")
#     if not system.date_time_value or days_delta(system.date_time_value) >= 7:
#         corpus = {}
#         games = [
#             game for game in Game.select() if get_game_stats(game).player_count > 5
#         ]  # min_player_count = 16 is better, because the tests say so
#         for game in games:
#             corpus[game] = get_game_stats(game).features
#         vectorizer = CountVectorizer()
#         X = vectorizer.fit_transform(corpus.values())
#         cosine_similarity_result = cosine_similarity(X, X)
#         for game_a, row in zip(games, cosine_similarity_result):
#             result = [
#                 (game_b.id, value) for game_b, value in zip(games, row) if value >= 0.5
#             ]
#             result = dict(sorted(result, key=itemgetter(1), reverse=True))
#             game_cbr, _ = GameCBR.get_or_create(game=game_a)
#             game_cbr.data = json.dumps(result)
#             game_cbr.save()
#         system.date_time_value = dt.datetime.now()
#         system.save()
#     game_cbr = GameCBR.get_or_none(game=target_game)
#     if game_cbr:
#         data = {
#             Game.get_by_id(game_id): value
#             for game_id, value in json.loads(game_cbr.data).items()
#         }
#         if len(data) > result_count + 1:
#             return dict(list(data.items())[1 : result_count + 1])
#         else:
#             return dict(list(data.items())[1:])
#     else:
#         return {}


# def get_cbr_for_user(user, result_count=9):
#     if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
#         print("get_cbr_for_user")
#         played_user_games = (
#             UserGame.select(UserGame.game, UserGame.score).where(UserGame.user == user).where(UserGame.playtime > 0)
#         )
#         played_games = [ug.game for ug in played_user_games]
#         user_games_with_score = played_user_games.where(UserGame.score != None)
#         games_with_score = [ug.game for ug in user_games_with_score]
#         result = {}
#         # best_game_cbr_result_count = 6 is better, because the tests say so
#         for user_game, game_cbr_result in zip(
#             user_games_with_score, [get_cbr_for_game(g, 6) for g in games_with_score]
#         ):
#             if game_cbr_result:
#                 for sim_game in game_cbr_result:
#                     if sim_game not in played_games and sim_game.rating >= 7:
#                         if sim_game.id not in result:
#                             result[sim_game.id] = (
#                                 user_game.score * game_cbr_result[sim_game]
#                             )
#                         else:
#                             result[sim_game.id] += (
#                                 user_game.score * game_cbr_result[sim_game]
#                             )
#         user_cbr, _ = UserCBR.get_or_create(user=user)
#         user_cbr.data = json.dumps(
#             dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
#         )
#         user_cbr.save()
#         user.last_cbr_update_time = dt.datetime.now()
#         user.save()
#     data = {
#         Game.get_by_id(game_id): value
#         for game_id, value in json.loads(
#             UserCBR.get_or_none(UserCBR.user == user).data
#         ).items()
#     }
#     if len(data) > result_count:
#         return dict(list(data.items())[:result_count])
#     else:
#         return data

db.rollback()
games = Game.select(Game.id)
for game in games:
    get_game_stats(game)

# user = User.get_by_id(76561198083927294)
# system, _ = System.get_or_create(key="GameCBR")
# system.date_time_value = None
# system.save()
# user.last_cbr_update_time = None
# user.save()
# print(get_cbr_for_user(user, 9))
