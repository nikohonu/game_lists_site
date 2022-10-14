from flask import Blueprint, jsonify, render_template, request

from game_lists_site.models import Game, GameStats
from game_lists_site.utils.utils import get_game_stats

bp = Blueprint("games", __name__, url_prefix="/games")


@bp.route("/")
def games():
    for game in Game.select():
        get_game_stats(game)
    game_stats = list(GameStats.select().where(GameStats.player_count > 0))
    game_stats = sorted(game_stats, key=lambda x: x.player_count, reverse=True)
    game_stats = sorted(game_stats, key=lambda x: x.rating, reverse=True)[:40]
    return render_template("games/games.html", game_stats=game_stats)
