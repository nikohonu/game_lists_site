from flask import Blueprint, abort

import game_lists_site.utils.steam as steam

bp = Blueprint('steam', __name__, url_prefix='/steam')


@bp.route('get-profile/<profile_id>')
def get_profile(profile_id: int):
    player = steam.get_profile(profile_id)
    if player:
        return player
    else:
        abort(404)


@bp.route('get-profile-games/<profile_id>')
def get_profile_games(profile_id: int):
    games = steam.get_profile_games(profile_id)
    if games:
        return games
    else:
        abort(404)
