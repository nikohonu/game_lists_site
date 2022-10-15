from telnetlib import GA
from flask import Blueprint, jsonify, render_template, request

from game_lists_site.models import Game, GameStats, UserGame
from peewee import fn
from game_lists_site.utils.utils import get_game_stats
import numpy as np

bp = Blueprint("games", __name__, url_prefix="/games")


@bp.route("/")
def games():
    for game in Game.select():
        get_game_stats(game)
    game_stats = list(GameStats.select().where(GameStats.player_count > 0))
    game_stats = sorted(game_stats, key=lambda x: x.player_count, reverse=True)
    game_stats = sorted(game_stats, key=lambda x: x.rating, reverse=True)[:40]
    return render_template("games/games.html", game_stats=game_stats)


@bp.route("stats")
def stats():
    stats = {}
    user_game = UserGame.select(UserGame.playtime, UserGame.score)
    games = Game.select()
    user_game_with_playtime = user_game.where(UserGame.playtime > 0)
    user_game_with_scores = user_game.where(UserGame.score > 0)
    games_with_release_date = games.where(Game.release_date != None)
    playtimes = np.array([ug.playtime for ug in user_game_with_playtime])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    stats["total_games"] = games.count()
    stats["hours_played"] = playtimes.sum() / 60
    stats["days_played"] = round(stats["hours_played"] / 24 * 10) / 10
    stats["hours_played"] = round(stats["hours_played"])
    stats["mean_playtime"] = round(playtimes.mean() / 60 * 100) / 100
    stats["playtime_standard_deviation"] = round(playtimes.std() / 60 * 100) / 100
    stats["mean_score"] = round(scores.mean() * 100) / 100
    stats["score_standard_deviation"] = round(scores.std() * 100) / 100
    stats["score_count"] = {}
    for i in range(1, 11):
        count = len(user_game.where(UserGame.score == i))
        if count != 0:
            stats["score_count"][i] = count
    stats["score_hours"] = {}
    for i in range(1, 11):
        hours = round(
            np.sum([ug.playtime for ug in user_game.where(UserGame.score == i)]) / 60
        )
        if hours != 0:
            stats["score_hours"][i] = hours
    stats["release_years_count"] = {}
    stats["release_years_hours"] = {}
    stats["release_years_mean"] = {}
    for game in games_with_release_date:
        year = game.release_date.year
        playtime = np.array(
            [ug.playtime for ug in user_game_with_playtime.where(UserGame.game == game)]
        ).sum()
        scores = [ug.score for ug in user_game_with_scores.where(UserGame.game == game)]
        if year in stats["release_years_count"]:
            stats["release_years_count"][year] += 1
            stats["release_years_hours"][year] += playtime
            stats["release_years_mean"][year] += scores
            if scores:
                print(scores)
                stats["release_years_mean"][year] += scores
        else:
            stats["release_years_count"][year] = 1
            stats["release_years_hours"][year] = playtime
            if scores:
                stats["release_years_mean"][year] = scores
            else:
                stats["release_years_mean"][year] = []
    for year in stats["release_years_hours"]:
        stats["release_years_hours"][year] = round(
            stats["release_years_hours"][year] / 60
        )
    years = []
    for year in stats["release_years_mean"]:
        if stats["release_years_mean"][year] and len(stats["release_years_mean"][year]) > 1:
            stats["release_years_mean"][year] = (
                round(np.mean(stats["release_years_mean"][year]) * 10) / 10
            )
        else:
            years.append(year)
    for year in years:
        stats["release_years_mean"].pop(year)
    stats["release_years_count"] = dict(
        sorted(stats["release_years_count"].items(), key=lambda x: x[0])
    )
    stats["release_years_hours"] = dict(
        sorted(stats["release_years_hours"].items(), key=lambda x: x[0])
    )
    stats["release_years_mean"] = dict(
        sorted(stats["release_years_mean"].items(), key=lambda x: x[0])
    )
    return render_template("games/stats.html", stats=stats)


@bp.route("stats/genres")
def genres():
    statistics = {}
    user_game = UserGame.select()
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    statistics["total_games"] = len(list(user_game))
    return render_template("games/features.html", statistics=statistics)


@bp.route("stats/tags")
def tags():
    statistics = {}
    user_game = UserGame.select()
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    statistics["total_games"] = len(list(user_game))
    return render_template("games/features.html", statistics=statistics)


@bp.route("stats/developer")
def developers():
    statistics = {}
    user_game = UserGame.select()
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    statistics["total_games"] = len(list(user_game))
    return render_template("games/features.html", statistics=statistics)
