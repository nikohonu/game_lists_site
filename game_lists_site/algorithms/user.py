import datetime as dt

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.algorithms.game import update_cbr_for_game
from game_lists_site.models import Game, System, User, UserGame
from game_lists_site.utilities import (
    ParametersManager,
    days_delta,
    get_game_vecs,
    get_readable_result_for_games,
    merge_dicts,
    normalize_dict,
    get_normalized_playtimes,
)


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
            users_games_playtimes = get_normalized_playtimes(p["min_player_count"], p["zscore"], True)
            user_games_playtimes = users_games_playtimes[user.id] if user.id in users_games_playtimes else []
            result = []
            for game in played_games:
                if game.id in user_games_playtimes.keys():
                    if game.cbr:
                        result.append(
                            {
                                "id": game.id,
                                "cbr": game.cbr,
                                "score": user_games_playtimes[game.id]
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
        result = {str(game.id): value for game, value in get_readable_result_for_games(merge_dicts(result)).items() if game not in played_games}
        user.cbr = result
        user.cbr_update_time = dt.datetime.now()
        user.save()
