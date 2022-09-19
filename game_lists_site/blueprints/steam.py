from flask import Blueprint, abort, jsonify
from flask_peewee.utils import get_object_or_404

import game_lists_site.utils.steam as steam

# from game_lists_site.models import SteamProfile, User

bp = Blueprint('steam', __name__, url_prefix='/steam')


@bp.route('get-profile/<profile_id>')
def get_profile(profile_id: int):
    player = steam.get_profile(profile_id)
    if player:
        return jsonify(player.__dict__)
    else:
        abort(404)


@bp.route('get-profile-apps/<profile_id>')
def get_profile_app(profile_id: int):
    profile_apps = steam.get_profile_apps(profile_id)
    if profile_apps:
        result = []
        for profile_app in profile_apps:
            if profile_app.steam_app.is_game:
                result.append({
                    'app_id': profile_app.steam_app.id,
                    'app_name': profile_app.steam_app.name,
                    'playtime': profile_app.playtime,
                })
        return jsonify(result)
    else:
        abort(404)


@bp.route('check-profile/<profile_id>')
def check_profile(profile_id: int):
    print(profile_id)
    user = get_object_or_404(User, User.steam_profile == profile_id)
    if user.last_games_update_time:
        return user.username
    else:
        return abort(404)
