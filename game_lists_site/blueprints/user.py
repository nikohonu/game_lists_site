import datetime as dt
import json

from flask import Blueprint, jsonify, render_template, request
from flask_peewee.utils import get_object_or_404
from game_lists_site.algorithms.user import update_cbr_for_user

import game_lists_site.utils.steam as steam
from game_lists_site.models import Game, User, UserGame
from game_lists_site.utilities import (
    days_delta,
    get_readable_result_for_games,
    update_game,
    update_game_score_stats,
    update_game_stats,
)

bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route("/<username>")
def user(username: str):
    user = get_object_or_404(User, User.username == username)
    if days_delta(user.last_update_time) >= 1:
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
            update_game_score_stats(ug.game)
            return jsonify({"id": id, "score": score})
    user = get_object_or_404(User, User.username == username)
    if days_delta(user.last_games_update_time) >= 1:
        owned_games = steam.get_owned_games(user.id)
        for owned_game in owned_games:
            game = update_game(owned_game["appid"])
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
        games = Game.select().join(UserGame).where(UserGame.user == user)
        for game in games:
            update_game_stats(game)
    user_games = (
        UserGame.select()
        .where(UserGame.user == user)
        .order_by(UserGame.playtime.desc())
    )
    return render_template("user/games.html", user_games=user_games, user=user)


@bp.route("/<username>/recommendations")
def recommendations(username: str):
    user = get_object_or_404(User, User.username == username)
    update_cbr_for_user(user)
    # hrs_result = get_hrs_for_user(user).keys()
    cbr_result = get_readable_result_for_games(user.cbr, 9)
    # mbcf_result = get_mbcf_for_user(user).keys()
    # mobcf_result = get_mobcf_for_user(user).keys()
    return render_template(
        "user/recommendations.html",
        user=user,
        cbr_result=cbr_result,
        # mbcf_result=mbcf_result,
        # mobcf_result=mobcf_result,
        # hrs_result=hrs_result,
    )
