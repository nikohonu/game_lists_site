import numpy as np
from flask import Blueprint, render_template, request
from flask_peewee.utils import get_object_or_404

from game_lists_site.models import (
    Developer,
    GameDeveloper,
    GameGenre,
    GameTag,
    Genre,
    Tag,
    User,
    UserGame,
)

bp = Blueprint("user_stats", __name__, url_prefix="/user")


@bp.route("/<username>/stats/overview", methods=["GET"])
def overview(username: str):
    user = get_object_or_404(User, User.username == username)
    stats = {}
    user_game = UserGame.select(UserGame.playtime, UserGame.score, UserGame.game).where(
        UserGame.user == user
    )
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    stats["total_games"] = len(list(user_game))
    stats["hours_played"] = round(playtimes.sum() / 60)
    stats["days_played"] = round(playtimes.sum() / 60 / 24 * 10) / 10
    stats["mean_playtime"] = round(playtimes.mean() / 60 * 100) / 100
    stats["playtime_standard_deviation"] = round(playtimes.std() / 60 * 100) / 100
    stats["mean_score"] = round(scores.mean() * 100) / 100
    stats["score_standard_deviation"] = round(scores.std() * 100) / 100
    stats["score_count"] = {}
    for i in range(1, 11):
        count = len(user_game.where(UserGame.score == i))
        if count:
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
    for ug in user_game.where(UserGame.playtime > 0):
        if ug.game.release_date == None:
            continue
        year = ug.game.release_date.year
        if year in stats["release_years_count"]:
            stats["release_years_count"][year] += 1
            stats["release_years_hours"][year] += ug.playtime / 60
        else:
            stats["release_years_count"][year] = 1
            stats["release_years_hours"][year] = ug.playtime / 60

    for ug in user_game.where(UserGame.score > 0):
        if ug.game.release_date == None:
            continue
        year = ug.game.release_date.year
        if year in stats["release_years_mean"]:
            stats["release_years_mean"][year].append(ug.score)
        else:
            stats["release_years_mean"][year] = [ug.score]
    for year in stats["release_years_hours"]:
        stats["release_years_hours"][year] = round(stats["release_years_hours"][year])
    for year in stats["release_years_mean"]:
        stats["release_years_mean"][year] = (
            round(np.mean(stats["release_years_mean"][year]) * 10) / 10
        )
    stats["release_years_count"] = dict(
        sorted(stats["release_years_count"].items(), key=lambda x: x[0])
    )
    stats["release_years_hours"] = dict(
        sorted(stats["release_years_hours"].items(), key=lambda x: x[0])
    )
    stats["release_years_mean"] = dict(
        sorted(stats["release_years_mean"].items(), key=lambda x: x[0])
    )
    return render_template("user/stats/overview.html", user=user, statistics=stats)


developers_fix = {
    "FromSoftwareInc": "FromSoftware",
    "Aspyr(Linux)": "Aspyr",
    "Aspyr(Mac)": "Aspyr",
    "FeralInteractive(Mac)": "FeralInteractive",
    "FeralInteractive(Linux)": "FeralInteractive",
}


def get_features_stats(user, feature_type, exclude_without_score=False):
    user_game = (
        UserGame.select(UserGame.game, UserGame.score, UserGame.playtime)
        .where(UserGame.user == user)
        .where(UserGame.playtime > 0)
    )
    if exclude_without_score:
        user_game = user_game.where(UserGame.score > 0)
    stats = {}
    for ug in user_game:
        match feature_type:
            case "genre":
                game_feature = (
                    Genre.select(Genre.name)
                    .join(GameGenre)
                    .where(GameGenre.game == ug.game)
                )
            case "tag":
                game_feature = (
                    Tag.select(Tag.name).join(GameTag).where(GameTag.game == ug.game)
                )
            case "developer":
                game_feature = (
                    Developer.select(Developer.name)
                    .join(GameDeveloper)
                    .where(GameDeveloper.game == ug.game)
                )
        for gf in game_feature:
            unified_feature_name = (
                gf.name.replace(" ", "").replace(",", "").replace(".", "")
            )
            if feature_type == "developer" and unified_feature_name in developers_fix:
                unified_feature_name = developers_fix[unified_feature_name]
            if unified_feature_name not in stats:
                stats[unified_feature_name] = {}
                stats[unified_feature_name]["name"] = gf.name
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
    exclude_without_score = request.args.get("exclude_without_score", False)
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats(user, "genre", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "user/stats/features.html",
        user=user,
        title="Genres",
        stats=stats,
        exclude_without_score=exclude_without_score,
    )


@bp.route("/<username>/stats/tags")
def tags(username: str):
    user = get_object_or_404(User, User.username == username)
    exclude_without_score = request.args.get("exclude_without_score", "")
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats(user, "tag", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "user/stats/features.html",
        user=user,
        title="Tags",
        stats=stats,
        exclude_without_score=exclude_without_score,
    )


@bp.route("/<username>/stats/developers")
def developers(username: str):
    user = get_object_or_404(User, User.username == username)
    exclude_without_score = request.args.get("exclude_without_score", False)
    exclude_without_score = exclude_without_score == "true"
    stats = get_features_stats(user, "developer", exclude_without_score)
    exclude_without_score = str(exclude_without_score).lower()
    return render_template(
        "user/stats/features.html",
        user=user,
        title="Developers",
        stats=stats,
        exclude_without_score=exclude_without_score,
    )
