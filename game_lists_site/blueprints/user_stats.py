import datetime as dt
import json

import numpy as np
from flask import Blueprint, jsonify, render_template, request
from flask_peewee.utils import get_object_or_404

import game_lists_site.utils.steam as steam
from game_lists_site.models import Game, GameGenre, User, UserGame
from game_lists_site.utils.utils import (
    days_delta,
    get_cbr_for_user,
    get_game,
    get_hrs_for_user,
    get_mbcf_for_user,
    get_mobcf_for_user,
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
    431960,
    607380,
    623990,
    700580,
]
free_game_ids = [440, 570, 950670, 450390]

bp = Blueprint("user_stats", __name__, url_prefix="/user")


@bp.route("/<username>/stats/overview")
def overview(username: str):
    user = get_object_or_404(User, User.username == username)
    statistics = {}
    user_game = UserGame.select().where(UserGame.user == user)
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    statistics["total_games"] = len(list(user_game))
    statistics["hours_played"] = round(playtimes.sum() / 60)
    statistics["days_played"] = round(playtimes.sum() / 60 / 24 * 10) / 10
    statistics["mean_playtime"] = round(playtimes.mean() / 60 * 100) / 100
    statistics["playtime_standard_deviation"] = round(playtimes.std() / 60 * 100) / 100
    statistics["mean_score"] = round(scores.mean() * 100) / 100
    statistics["score_standard_deviation"] = round(scores.std() * 100) / 100
    statistics["score_count"] = {}
    for i in range(1, 11):
        count = len(user_game.where(UserGame.score == i))
        if count:
            statistics["score_count"][i] = count
    statistics["score_hours"] = {}
    for i in range(1, 11):
        hours = round(
            np.sum([ug.playtime for ug in user_game.where(UserGame.score == i)]) / 60
        )
        if hours != 0:
            statistics["score_hours"][i] = hours
    statistics["release_years_count"] = {}
    statistics["release_years_hours"] = {}
    statistics["release_years_mean"] = {}
    for ug in user_game.where(UserGame.playtime > 0):
        if ug.game.release_date == None:
            continue
        year = ug.game.release_date.year
        if year in statistics["release_years_count"]:
            statistics["release_years_count"][year] += 1
            statistics["release_years_hours"][year] += ug.playtime / 60
        else:
            statistics["release_years_count"][year] = 1
            statistics["release_years_hours"][year] = ug.playtime / 60

    for ug in user_game.where(UserGame.score > 0):
        if ug.game.release_date == None:
            continue
        year = ug.game.release_date.year
        if year in statistics["release_years_mean"]:
            statistics["release_years_mean"][year].append(ug.score)
        else:
            statistics["release_years_mean"][year] = [ug.score]
    for year in statistics["release_years_hours"]:
        statistics["release_years_hours"][year] = round(
            statistics["release_years_hours"][year]
        )
    for year in statistics["release_years_mean"]:
        statistics["release_years_mean"][year] = (
            round(np.mean(statistics["release_years_mean"][year]) * 10) / 10
        )
    statistics["release_years_count"] = dict(
        sorted(statistics["release_years_count"].items(), key=lambda x: x[0])
    )
    statistics["release_years_hours"] = dict(
        sorted(statistics["release_years_hours"].items(), key=lambda x: x[0])
    )
    statistics["release_years_mean"] = dict(
        sorted(statistics["release_years_mean"].items(), key=lambda x: x[0])
    )
    return render_template("user/stats/overview.html", user=user, statistics=statistics)


@bp.route("/<username>/stats/genres")
def genres(username: str):
    user = get_object_or_404(User, User.username == username)
    user_game = UserGame.select().where(UserGame.user == user).where(UserGame.playtime > 0)
    stats = {}
    stats["by_count"] = {}
    for ug in user_game:
        game_genre = GameGenre.select().where(GameGenre.game == ug.game)
        for gg in game_genre:
            genre_name = gg.genre.name 
            if genre_name not in stats["by_count"]:
                stats["by_count"][genre_name] = {}
                stats["by_count"][genre_name]["games"] = {ug}
            else:
                stats["by_count"][genre_name]["games"].add(ug)
    for genre in stats["by_count"]:
        stats["by_count"][genre]["count"] = len(stats["by_count"][genre]["games"])
        scores = [ug.score for ug in stats["by_count"][genre]["games"] if ug.score != None]
        if scores:
            stats["by_count"][genre]["mean"] = round(np.mean(scores) * 100) / 100
        else:
            stats["by_count"][genre]["mean"] = 0 
        stats["by_count"][genre]["time"] = np.sum([ug.playtime for ug in stats["by_count"][genre]["games"]])
    stats["by_count"] = dict(sorted(stats["by_count"].items(), key= lambda x: x[1]["count"], reverse=True))
    for genre in stats["by_count"]:
        stats["by_count"][genre]['games'] = sorted(stats["by_count"][genre]["games"], key = lambda x: x.playtime)
    stats["by-mean-score"] = {}
    stats["by-time-played"] = {}
    return render_template("user/stats/genres.html", user=user, stats=stats)


@bp.route("/<username>/stats/tags")
def tags(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = {}
    return render_template("user/stats/tags.html", user=user, stats=stats)


@bp.route("/<username>/stats/developers")
def developers(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = {}
    return render_template("user/stats/developers.html", user=user, stats=stats)
