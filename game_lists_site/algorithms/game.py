import datetime as dt

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.models import Game, System
from game_lists_site.utilities import (
    ParametersManager,
    days_delta,
    get_game_vecs,
    merge_dicts,
    normalize_dict,
)


def update_cbr_for_game(**current_parameters):
    p = ParametersManager("cbr_for_game", current_parameters, {"min_player_count": 10})
    system, _ = System.get_or_create(key="cbr_for_game")
    if days_delta(system.date_time) > 30 or p.is_diff_last_current():
        print("update cbr for game")
        Game.update({Game.cbr: None}).execute()
        games = Game.select(Game.id, Game.features).where(
            (Game.features != None)
            & (Game.player_count > p["min_player_count"])
        )
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform([g.features for g in games])
        csr = cosine_similarity(X, X)
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


def update_mbcf_for_games(**current_parameters):
    p = ParametersManager("mbcf_for_game", current_parameters, {"min_player_count": 10, "min_game_count": 10})
    system, _ = System.get_or_create(key="mbcf_for_game")
    if (days_delta(system.date_time) > 30) or p.is_diff_last_current():
        print("update mbcf for game")
        Game.update({Game.mbcf: None}).execute()
        game_ids, _, game_vecs = get_game_vecs(p['min_player_count'], p['min_game_count'])
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


def update_hr_for_games(**current_parameters):
    p = ParametersManager("hr_for_game", current_parameters, {"cbr_coef": 0.75, "mbcf_coef": 0.25})
    system, _ = System.get_or_create(key="hr_for_game")
    if (
        days_delta(system.date_time) > 30 
        or p.is_diff_last_current()
    ):
        print("update hr for game")
        Game.update({Game.hr: None}).execute()
        games = Game.select(Game.id, Game.cbr, Game.mbcf)
        for game in games:
            cbr_result = game.cbr
            mbcf_result = game.mbcf
            game.hr = merge_dicts(
                [
                    normalize_dict(cbr_result, p['cbr_coef']) if cbr_result else [],
                    normalize_dict(mbcf_result, p['mbcf_coef']) if mbcf_result else [],
                ]
            )
            if not game.hr:
                game.hr = None
        Game.bulk_update(games, [Game.hr])
        system.date_time = dt.datetime.now()
        system.save()