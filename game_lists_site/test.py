import datetime as dt
import json
import random
from operator import itemgetter

import numpy as np
from sklearn import preprocessing
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.models import (Game, GameCBR, GameDeveloper, GameGenre,
                                    GameStats, GameTag, System, User, UserGame)
                                    


def days_delta(datetime):
    current_date = dt.datetime.now()
    return (current_date - datetime).days

game_stats_cache = {}

def get_game_stats(game: Game):
    if game in game_stats_cache:
        return game_stats_cache[game]
    game_stats = GameStats.get_or_none(GameStats.game == game)
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        game_stats.player_count = len(
            UserGame.select().where(UserGame.game == game).where(UserGame.playtime > 0))
        # features
        features = []
        features += [game_developer.developer.name.replace(
            " ", "") for game_developer in GameDeveloper.select().where(GameDeveloper.game == game)]
        features += [game_genre.genre.name.replace(
            " ", "") for game_genre in GameGenre.select().where(GameGenre.game == game)]
        features += [game_tag.tag.name.replace(' ', '')
                     for game_tag in GameTag.select().where(GameTag.game == game)]
        game_stats.features = " ".join(features)
        # features end
        game_stats.last_update_time = dt.datetime.now()
        game_stats.save()
    game_stats_cache[game] = game_stats
    return game_stats_cache[game]


def get_cbr_for_games(target_games, min_player_count, result_count):
    corpus = {}
    games = [game for game in Game.select(
    ) if get_game_stats(game).player_count >= min_player_count]
    for game in games:
        corpus[game] = get_game_stats(game).features
    vectorizer = CountVectorizer()
    X = vectorizer.fit_transform(corpus.values())
    cosine_similarity_result = cosine_similarity(X, X)
    result = {}
    for game_a, row in zip(games, cosine_similarity_result):
        result[game_a] = [(game_b, value) for game_b, value in zip(games, row) if value >= 0.5]
        result[game_a] = sorted(result[game_a], key=itemgetter(1), reverse=True)[1:result_count+1]
        result[game_a] = dict(result[game_a])
    for game in target_games:
        if game in result:
            yield result[game]
        else:
            yield None


def get_cbr_for_user(user_games_with_score, played_games, min_player_count, game_cbr_result_count, result_count):
    games_with_score = [ug.game for ug in user_games_with_score]
    result = {}
    for user_game, game_cbr_result in zip(user_games_with_score, get_cbr_for_games(games_with_score, min_player_count, game_cbr_result_count)):
        if game_cbr_result:
            for sim_game in game_cbr_result:
                if sim_game not in played_games:
                    if sim_game not in result:
                        result[sim_game] = user_game.score * \
                            game_cbr_result[sim_game]
                    else:
                        result[sim_game] += user_game.score * \
                            game_cbr_result[sim_game]
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True)[:result_count])


def do_test(user_id, min_player_count, game_cbr_result_count, result_count):
    user = User.get_by_id(user_id)
    played_user_games = UserGame.select().where(
        UserGame.user == user).where(UserGame.playtime > 0)
    user_games_with_score = played_user_games.where(UserGame.score != None)
    quantile = np.quantile(
        [ug.last_played for ug in user_games_with_score], 0.90)
    input_user_games = [
        ug for ug in user_games_with_score if ug.last_played <= quantile]
    input_games = [ug.game for ug in input_user_games]
    check_user_games = [
        ug for ug in user_games_with_score if ug.last_played > quantile]
    played_games = set()
    for ug in input_user_games:
        played_games.add(ug.game)
    for ug in played_user_games:
        if ug not in check_user_games:
            played_games.add(ug.game)
    played_games = list(played_games)
    result = get_cbr_for_user(input_user_games, played_games,
                              min_player_count, game_cbr_result_count, result_count)

    accuracy = 0
    for ug in check_user_games:
        if ug.game in result:
            accuracy += 1
    return accuracy/len(check_user_games)


def main():
    # best_result_count = 43
    # best_game_cbr_result_count = 4
    # best_min_player_count = 9
    # best_accuracy = 0.26
    best_result_count = 9
    best_game_cbr_result_count = 6
    best_min_player_count = 16
    best_accuracy = 0.24
    user_ids = [User.get_by_id(user_id) for user_id in [76561198083927294, 76561198091812571, 76561198094109207, 76561198394079733]]
    for i in range(100):
        accuracies = []
        min_player_count = random.randrange(10, 21)
        game_cbr_result_count = random.randrange(1, 30)
        result_count = 9
        # result_count = 16
        # result_count = 30
        for user_id in user_ids:
            accuracies.append(do_test(user_id, min_player_count,
                            game_cbr_result_count, result_count))
        accuracy = np.average(accuracies)
        print("-"*10 + f"Stage {i}" + "-"*10)
        print('result_count:' + str(result_count))
        print('game_cbr_result_count:' + str(game_cbr_result_count))
        print('min_player_count:' + str(min_player_count))
        print('accuracy:' + str(accuracy))
        # if accuracy >= 0.20 and result_count < best_result_count:
        if accuracy > best_accuracy:
            best_result_count = result_count
            best_game_cbr_result_count = game_cbr_result_count
            best_min_player_count = min_player_count
            best_accuracy = accuracy
    print("-"*10 + "Best" + "-"*10)
    print('result_count:' + str(best_result_count))
    print('game_cbr_result_count:' + str(best_game_cbr_result_count))
    print('min_player_count:' + str(best_min_player_count))
    print('accuracy:' + str(best_accuracy))
    # result = do_test(input_user_games)
    # print(result)

if __name__ == "__main__":
    main()