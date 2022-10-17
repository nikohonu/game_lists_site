import numpy as np
from flask import Blueprint, jsonify, render_template, request
from peewee import fn

from game_lists_site.models import (
    Game,
    GameDeveloper,
    GameGenre,
    GameStats,
    GameTag,
    UserGame,
)
from game_lists_site.utils.utils import get_game_stats

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
        if (
            stats["release_years_mean"][year]
            and len(stats["release_years_mean"][year]) > 1
        ):
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


developers_fix = {
    "FromSoftwareInc": "FromSoftware",
    "Aspyr(Linux)": "Aspyr",
    "Aspyr(Mac)": "Aspyr",
    "FeralInteractive(Mac)": "FeralInteractive",
    "FeralInteractive(Linux)": "FeralInteractive",
}


def get_features_stats(feature_type, exclude_without_score=False):
    game_stats = GameStats.select().where(GameStats.total_playtime > 0)
    if exclude_without_score:
        game_stats = game_stats.where(GameStats.rating > 0)
    stats = {}
    for gs in game_stats:
        match feature_type:
            case "genre":
                game_feature = GameGenre.select().where(GameGenre.game == gs.game)
            case "tag":
                game_feature = GameTag.select().where(GameTag.game == gs.game)
            case "developer":
                game_feature = GameDeveloper.select().where(GameDeveloper.game == gs.game)
        for gg in game_feature:
            match feature_type:
                case "genre":
                    feature_name: str = gg.genre.name
                case "tag":
                    feature_name: str = gg.tag.name
                case "developer":
                    feature_name: str = gg.developer.name
            unified_feature_name = (
                feature_name.replace(" ", "").replace(",", "").replace(".", "")
            )
            if feature_type == "developer" and unified_feature_name in developers_fix:
                unified_feature_name = developers_fix[unified_feature_name]
            if unified_feature_name not in stats:
                stats[unified_feature_name] = {}
                stats[unified_feature_name]["name"] = feature_name
                stats[unified_feature_name]["games"] = {gs}
            else:
                stats[unified_feature_name]["games"].add(gs)
    user_game = UserGame.select().where(UserGame.score != 0)
    for feature in stats:
        stats[feature]["count"] = len(stats[feature]["games"])
        scores = []
        for g in [gs.game for gs in stats[feature]["games"] if gs.rating > 0]:
            scores += [ug.score for ug in user_game.where(UserGame.game == g)]
        if scores:
            stats[feature]["score"] = round(np.mean(scores) * 100) / 100
        else:
            stats[feature]["score"] = 0
        stats[feature]["playtime"] = np.sum(
            [gs.total_playtime for gs in stats[feature]["games"]]
        )
    stats = dict(
        sorted(
            [(key, value) for key, value in stats.items() if value["count"] >= 2],
            key=lambda x: x[1]["count"],
            reverse=True,
        )
    )
    for feature in stats:
        stats[feature]["games"] = sorted(
            stats[feature]["games"], key=lambda x: x.total_playtime, reverse=True
        )
    return stats


@bp.route("stats/genres")
def genres():
    exclude_without_score = request.args.get("exclude_without_score", False)
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats("genre", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "games/features.html", title="Genres", stats=stats, exclude_without_score=exclude_without_score
    )

@bp.route("stats/tags")
def tags():
    exclude_without_score = request.args.get("exclude_without_score", False)
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats("tag", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "games/features.html", title="Tags", stats=stats, exclude_without_score=exclude_without_score
    )

@bp.route("stats/developers")
def developers():
    exclude_without_score = request.args.get("exclude_without_score", False)
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats("developer", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "games/features.html", title="Developers", stats=stats, exclude_without_score=exclude_without_score
    )