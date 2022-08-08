from flask import Blueprint, abort, render_template

from game_lists_site.blueprints.steam import (get_player_dict,
                                              get_player_games_dict)
from game_lists_site.db import get_db

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/<name>')
def user(name: str):
    db = get_db()
    steam_id = db.execute(
        'SELECT steam_id FROM user WHERE username = ?',
        (name,)
    ).fetchone()
    if steam_id:
        steam_id = steam_id[0]
    else:
        abort(404)
    player = get_player_dict(steam_id)
    games = get_player_games_dict(steam_id)
    if player:
        return render_template(
            'user/user.html', name=name, player=player, games=games)
    else:
        return abort(404)
