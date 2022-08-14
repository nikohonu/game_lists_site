from flask import Blueprint, abort, render_template

from game_lists_site.db import get_db
from game_lists_site.utils.steam import get_profile, get_profile_apps

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
    steam_profile_apps = sorted(list(get_profile_apps(steam_profile_id)), key= lambda x: x.playtime, reverse=True)
    if steam_profile:
        return render_template('user/user.html', username=username,
                               steam_profile=steam_profile, steam_profile_apps=steam_profile_apps)
    else:
        return abort(404)

@bp.route('/<username>/recommendation')
def recommendation(username: str):
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
    steam_profile_apps = sorted(list(get_profile_apps(steam_profile_id)), key= lambda x: x.playtime, reverse=True)
    if steam_profile:
        return render_template('user/recommendation.html', username=username,
                               steam_profile=steam_profile, steam_profile_apps=steam_profile_apps)
    else:
        return abort(404)

