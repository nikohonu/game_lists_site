from flask import Blueprint, abort, render_template

from game_lists_site.db import get_db
from game_lists_site.utils.steam import get_profile

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/<username>')
def user(username: str):
    db = get_db()
    steam_profile_id = db.execute(
        'SELECT steam_profile_id FROM user WHERE username = ?',
        (username,)
    ).fetchone()
    if steam_profile_id:
        steam_profile_id = steam_profile_id[0]
    else:
        abort(404)
    steam_profile = get_profile(steam_profile_id)
    # games = get_profile(steam_profile_id)
    games = []
    if steam_profile:
        return render_template('user/user.html', username=username,
                               steam_profile=steam_profile, games=games)
    else:
        return abort(404)
