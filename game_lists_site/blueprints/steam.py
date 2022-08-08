import time

from flask import Blueprint, abort

from game_lists_site.db import get_db
from game_lists_site.utils.steam_api import (get_owned_games,
                                             get_player_summaries)

bp = Blueprint('steam', __name__, url_prefix='/steam')


def get_player_dict(steam_id):
    db = get_db()

    def get_player_from_db(steam_id):
        player = db.execute(
            'SELECT * FROM player WHERE steam_id = ?',
            (steam_id,)
        ).fetchone()
        if player:
            player = {
                'steam_id': player[0],
                'is_public': bool(player[1]),
                'name': player[2],
                'url': player[3],
                'avatar_url': player[4],
                'time_created': player[5],
                'update_time': player[6]
            }
            return player
    player = get_player_from_db(steam_id)
    if not player:
        response = get_player_summaries(steam_id)['response']
        if len(response['players']) == 0:
            return None
        else:
            raw_player = response['players'][0]
            db.execute(
                'INSERT INTO player (steam_id, is_public, name, url, '
                'avatar_url, time_created, update_time) VALUES (?, ?, ?, ?, ?, ?, '
                '?)',
                (raw_player['steamid'],
                 raw_player['communityvisibilitystate'] == 3,
                 raw_player['personaname'],
                 raw_player['profileurl'],
                 raw_player['avatarfull'],
                 raw_player['timecreated'],
                 round(time.time())
                 ))
            db.commit()
            return get_player_from_db(steam_id)
    else:
        return player


def get_player_games_dict(steam_id):
    response = get_owned_games(steam_id)['response']
    if response and len(response['games']) != 0:
        return sorted(
            response['games'],
            key=lambda x: x['playtime_forever'],
            reverse=True)
    else:
        return None


@bp.route('get-player/<steam_id>')
def get_player(steam_id: int):
    player = get_player_dict(steam_id)
    if player:
        return player
    else:
        abort(404)


@bp.route('get-player-games/<steam_id>')
def get_player_games(steam_id: int):
    games = get_player_games_dict(steam_id)
    if games:
        return games
    else:
        abort(404)
