import numpy as np
from flask import Blueprint, render_template
from flask_peewee.utils import get_object_or_404

from game_lists_site.models import GameDeveloper, GameGenre, GameTag, User, UserGame

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


developers_fix = {
    "FromSoftwareInc": "FromSoftware",
    "Aspyr(Linux)": "Aspyr",
    "Aspyr(Mac)": "Aspyr",
    "FeralInteractive(Mac)": "FeralInteractive",
    "FeralInteractive(Linux)": "FeralInteractive",
}


def get_features_stats(user, feature_type):
    user_game = (
        UserGame.select().where(UserGame.user == user).where(UserGame.playtime > 0)
    )
    stats = {}
    for ug in user_game:
        match feature_type:
            case "genre":
                game_feature = GameGenre.select().where(GameGenre.game == ug.game)
            case "tag":
                game_feature = GameTag.select().where(GameTag.game == ug.game)
            case "developer":
                game_feature = GameDeveloper.select().where(
                    GameDeveloper.game == ug.game
                )
        for gg in game_feature:
            match feature_type:
                case "genre":
                    feature_name: str = gg.genre.name  # this
                case "tag":
                    feature_name: str = gg.tag.name  # this
                case "developer":
                    feature_name: str = gg.developer.name  # this
            unified_feature_name = (
                feature_name.replace(" ", "").replace(",", "").replace(".", "")
            )
            if feature_type == "developer" and unified_feature_name in developers_fix:
                unified_feature_name = developers_fix[unified_feature_name]
            if unified_feature_name not in stats:
                stats[unified_feature_name] = {}
                stats[unified_feature_name]["name"] = feature_name
                stats[unified_feature_name]["games"] = {ug}
            else:
                stats[unified_feature_name]["games"].add(ug)
    for feature in stats:
        stats[feature]["count"] = len(stats[feature]["games"])
        scores = [ug.score for ug in stats[feature]["games"] if ug.score != None]
        if scores:
            stats[feature]["score"] = round(np.mean(scores) * 100) / 100
        else:
            stats[feature]["score"] = 0
        stats[feature]["playtime"] = np.sum(
            [ug.playtime for ug in stats[feature]["games"]]
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
            stats[feature]["games"], key=lambda x: x.playtime, reverse=True
        )
    return stats


@bp.route("/<username>/stats/genres")
def genres(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = get_features_stats(user, "genre")
    return render_template(
        "user/stats/features.html", user=user, title="Genres", stats=stats
    )


@bp.route("/<username>/stats/tags")
def tags(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = get_features_stats(user, "tag")
    return render_template(
        "user/stats/features.html", user=user, title="Tags", stats=stats
    )


@bp.route("/<username>/stats/developers")
def developers(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = get_features_stats(user, "developer")
    return render_template(
        "user/stats/features.html", user=user, title="Developers", stats=stats
    )
