from flask import Blueprint, render_template, current_app

from game_lists_site.db import get_db
from requests import get

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/<name>')
def user(name: str):
    db = get_db()
    steam_id = db.execute(
        'SELECT steam_id FROM user WHERE username = ?',
        (name,)
    ).fetchone()
    steam_id = steam_id[0] if steam_id else None
    url = current_app.config['STEAM_SERVER'] + f'/get-player/{steam_id}'
    request = get(url)
    result = request.json()
    steam_url = result['profile_url']
    steam_name = result['name']
    return render_template('user/user.html', name=name, steam_id=steam_id, steam_url=steam_url, steam_name=steam_name)
