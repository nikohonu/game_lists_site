import datetime as dt

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.algorithms.game import update_cbr_for_game
from game_lists_site.models import Game, System, User, UserGame, db
from game_lists_site.utilities import (
    ParametersManager,
    days_delta,
    get_game_vecs,
    get_normalized_playtimes,
    get_readable_result_for_games,
    merge_dicts,
    normalize_dict,
    slice_dict,
)

db.rollback()


def update_cbr_for_user(user, **current_parameters):
    p = ParametersManager(
        "cbr_for_user",
        current_parameters,
        {"min_player_count": 12, "cbr_for_game_result_count": 2, "zscore": False},
    )
    if days_delta(user.cbr_update_time) >= 1 or p.is_diff_last_current():
        update_cbr_for_game(min_player_count=p["min_player_count"])
        print(f'update cbr for "{user.username}"')
        user.cbr = None
        played_games = (
            Game.select(Game.id, Game.cbr, UserGame.score)
            .join(UserGame)
            .where((UserGame.user == user) & (UserGame.playtime > 0))
        )
        games_with_score = played_games.where((UserGame.score > 0) & (Game.cbr != None))
        # use normalized playtimes if not enough games with score
        if games_with_score.count() < 10:
            users_games_playtimes = get_normalized_playtimes(
                min_player_count=p["min_player_count"],
                zscore=p["zscore"],
                user_first=True,
            )
            user_games_playtimes = (
                users_games_playtimes[user.id]
                if user.id in users_games_playtimes
                else []
            )
            result = []
            for game in played_games:
                if game.id in user_games_playtimes.keys():
                    if game.cbr:
                        result.append(
                            {
                                "id": game.id,
                                "cbr": game.cbr,
                                "score": user_games_playtimes[game.id],
                            }
                        )
                games_with_score = result
        else:
            games_with_score = games_with_score.dicts()
        # calc result
        result = []
        for game_a_dict in games_with_score:
            result.append(
                {
                    key: value * game_a_dict["score"]
                    for key, value in list(game_a_dict["cbr"].items())[
                        1 : p["cbr_for_game_result_count"] + 1
                    ]
                }
            )
        result = {
            str(game.id): value
            for game, value in get_readable_result_for_games(
                merge_dicts(result)
            ).items()
            if game not in played_games and game.rating >= 7
        }
        user.cbr = result
        user.cbr_update_time = dt.datetime.now()
        user.save()


def update_similar_users(**current_parameters):
    p = ParametersManager(
        "similar_users",
        current_parameters,
        {"min_game_count": 10, "min_player_count": 10},
    )
    system, _ = System.get_or_create(key="user_spipimilarity")
    if days_delta(system.date_time) > 15 or p.is_diff_last_current():
        print("update similar users")
        _, user_ids, game_vecs = get_game_vecs(
            p["min_player_count"], p["min_game_count"]
        )
        user_vecs = np.flip(np.rot90(game_vecs), 0)
        users = [User.get_by_id(user_id) for user_id in user_ids]
        user_vecs = np.corrcoef(user_vecs)
        for user_a, row in zip(users, user_vecs):
            user_a.similar_users = dict(
                sorted(
                    [(user_id_b, value) for user_id_b, value in zip(user_ids, row)],
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
        User.bulk_update(users, [User.similar_users])
        system.date_time = dt.datetime.now()
        system.save()


def update_mbcf_for_user(user, **current_parameters):
    p = ParametersManager(
        "mbcf_for_user",
        current_parameters,
        {"sim_user_count": 10, "min_player_count": 10, "min_game_count": 10},
    )
    if p.is_diff_last_current():
        User.update({User.mbcf_update_time: None}).execute()
    if days_delta(user.mbcf_update_time) > 1 or p.is_diff_last_current():
        update_similar_users()
        print(f'update mbcf for "{user.username}"')
        if not user.similar_users:
            return
        played_games = (
            Game.select(Game.id, Game.cbr, UserGame.score)
            .join(UserGame)
            .where((UserGame.user == user) & (UserGame.playtime > 0))
        )
        normalized_playtimes = get_normalized_playtimes(
            min_player_count=p["min_player_count"], zscore=False, user_first=True
        )
        result = []
        similar_users = slice_dict(user.similar_users, 1, p["sim_user_count"] + 1)
        for user_id, coef in similar_users.items():
            if user_id in normalized_playtimes:
                result.append(
                    {
                        key: value * coef
                        for key, value in normalized_playtimes[user_id].items()
                    }
                )
        user.mbcf = {
            str(game.id): value
            for game, value in get_readable_result_for_games(
                merge_dicts(result)
            ).items()
            if game not in played_games and game.rating >= 7
        }
        user.mbcf_update_time = dt.datetime.now()
        user.save()
