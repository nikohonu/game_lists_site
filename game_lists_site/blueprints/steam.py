from flask import Blueprint, abort, jsonify
from flask_peewee.utils import get_object_or_404

import game_lists_site.utils.steam as steam
from game_lists_site.models import User

bp = Blueprint("steam", __name__, url_prefix="/steam")


@bp.route("get-player-summary/<steam_id>")
def get_player_summary(steam_id: int):
    player = steam.get_player_summary(steam_id)
    if player:
        return jsonify(player)
    else:
        abort(404)


@bp.route("get-owned-games/<user_id>")
def get_profile_app(user_id: int):
    user_apps = steam.get_owned_games(user_id)
    if user_apps:
        return jsonify(user_apps)
    else:
        abort(404)


@bp.route("check-profile/<profile_id>")
def check_profile(profile_id: int):
    print(profile_id)
    user = get_object_or_404(User, User.id == profile_id)
    if user.last_games_update_time:
        return user.username
    else:
        return abort(404)


@bp.route("check-games/<user_id>")
def check_games(user_id: int):
    user = get_object_or_404(User, User.id == user_id)
    return str(user.last_games_update_time != None)
