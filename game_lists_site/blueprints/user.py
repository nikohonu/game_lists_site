import datetime as dt
import json

import numpy as np
from flask import Blueprint, jsonify, render_template, request
from flask_peewee.utils import get_object_or_404

import game_lists_site.utils.steam as steam
from game_lists_site.models import Game, User, UserGame
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

bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route("/<username>")
def user(username: str):
    user = get_object_or_404(User, User.username == username)
    if not user.last_update_time or days_delta(user.last_update_time) >= 1:
        player_summary = steam.get_player_summary(user.id)
        if player_summary:
            user.avatar_url = player_summary["avatarfull"]
            user.profile_url = player_summary["profileurl"]
            user.last_update_time = dt.datetime.now()
            user.save()
    return render_template("user/user.html", user=user)


@bp.route("/<username>/games", methods=["GET", "POST"])
def games(username: str):
    if request.method == "POST":
        data = json.loads(request.data.decode("utf-8"))
        if "id" in data and "score" in data:
            id = int(data["id"])
            user = get_object_or_404(User, User.username == username)
            game = get_object_or_404(Game, Game.id == id)
            score = max(min(int(data["score"]), 10), 0) if data["score"] else 0
            ug = get_object_or_404(
                UserGame, UserGame.user == user, UserGame.game == game
            )
            ug.score = score if score != 0 else None
            ug.save()
            return jsonify({"id": id, "score": score})
    user = get_object_or_404(User, User.username == username)
    if not user.last_games_update_time or days_delta(user.last_games_update_time) >= 1:
        owned_games = steam.get_owned_games(user.id)
        for owned_game in owned_games:
            if owned_game["appid"] in not_game_ids:
                continue
            if (
                owned_game["appid"] in free_game_ids
                and owned_game["playtime_forever"] == 0
            ):
                continue
            game = get_game(owned_game["appid"])
            if not game:
                continue
            last_played = (
                None
                if owned_game["rtime_last_played"] == 0
                else dt.datetime.fromtimestamp(owned_game["rtime_last_played"])
            )
            user_game, _ = UserGame.get_or_create(user=user, game=game)
            user_game.last_played = last_played
            user_game.playtime = owned_game["playtime_forever"]
            user_game.save()
        user.last_games_update_time = dt.datetime.now()
        user.save()
    user_games = (
        UserGame.select()
        .where(UserGame.user == user)
        .order_by(UserGame.playtime.desc())
    )
    return render_template("user/games.html", user_games=user_games, user=user)


@bp.route("/<username>/recommendations")
def recommendations(username: str):
    user = get_object_or_404(User, User.username == username)
    cbr_result = get_cbr_for_user(user, 9).keys()
    mbcf_result = get_mbcf_for_user(user, 9).keys()
    mobcf_result = get_mobcf_for_user(user, 9).keys()
    hrs_result = get_hrs_for_user(user, 9).keys()
    return render_template(
        "user/recommendations.html",
        user=user,
        cbr_result=cbr_result,
        mbcf_result=mbcf_result,
        mobcf_result=mobcf_result,
        hrs_result=hrs_result,
    )


@bp.route("/<username>/statistics")
def statistics(username: str):
    user = get_object_or_404(User, User.username == username)
    statistics = {}
    user_game = UserGame.select().where(UserGame.user == user)
    playtimes = np.array([ug.playtime for ug in user_game.where(UserGame.playtime > 0)])
    scores = np.array([ug.score for ug in user_game.where(UserGame.score > 0)])
    statistics['total_games'] = len(list(user_game))
    statistics['hours_played'] = round(playtimes.sum() / 60)
    statistics['days_played'] = round(playtimes.sum() / 60 / 24 * 10) / 10
    statistics['mean_playtime'] = round(playtimes.mean()  / 60 * 100) / 100
    statistics['playtime_standard_deviation'] = round(playtimes.std() / 60 * 100) / 100
    statistics['mean_score'] = round(scores.mean() * 100) / 100
    statistics['score_standard_deviation'] = round(scores.std() * 100) / 100
    return render_template('user/statistics.html', user=user, statistics=statistics)
