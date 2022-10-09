from bs4 import BeautifulSoup
from flask import Blueprint, abort, render_template

from game_lists_site.models import GameDeveloper, GameGenre, GameTag
from game_lists_site.utils.utils import get_cbr_for_game, get_game, get_mbcf_for_game

bp = Blueprint("game", __name__, url_prefix="/game")


@bp.route("<game_id>/<game_name>")
def game(game_id, game_name):
    game = get_game(game_id)
    if not game:
        abort(404)
    developers = [
        gd.developer.name
        for gd in GameDeveloper.select().where(GameDeveloper.game == game)
    ]
    genres = [gg.genre.name for gg in GameGenre.select().where(GameGenre.game == game)]
    tags = [gt.tag.name for gt in GameTag.select().where(GameTag.game == game)]
    short_description = BeautifulSoup(game.description, "html.parser").get_text(
        separator=" "
    )
    short_description = short_description[: min(500, len(short_description))]
    cbr_result = get_cbr_for_game(game, 9)
    mbcf_result = get_mbcf_for_game(game, 9)
    return render_template(
        "game.html",
        game=game,
        developers=developers,
        genres=genres,
        tags=tags,
        short_description=short_description,
        cbr_result=cbr_result,
        mbcf_result=mbcf_result,
    )
