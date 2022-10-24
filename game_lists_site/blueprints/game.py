from bs4 import BeautifulSoup
from flask import Blueprint, abort, render_template

from game_lists_site.models import Game, GameDeveloper, GameGenre, GameTag
from game_lists_site.utilities import (
    slice_dict,
    update_cbr_for_game,
    update_game,
    update_hr_for_games,
    update_mbcf_for_games,
)

bp = Blueprint("game", __name__, url_prefix="/game")

def get_readable_result(d: dict, size: int):
    d = slice_dict(d, 1, size + 1)
    return {Game.get_by_id(int(game_id)): value for game_id, value in d.items()}

@bp.route("<game_id>/<game_name>")
def game(game_id, game_name):
    if not update_game(game_id):
        abort(404)
    game = Game.get_by_id(game_id)
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
    update_cbr_for_game()
    update_mbcf_for_games()
    update_hr_for_games()
    cbr_result = get_readable_result(game.cbr, 9)
    mbcf_result = get_readable_result(game.mbcf, 9)
    hr_result = get_readable_result(game.hr, 9)
    return render_template(
        "game.html",
        game=game,
        developers=developers,
        genres=genres,
        tags=tags,
        short_description=short_description,
        cbr_result=cbr_result,
        mbcf_result=mbcf_result,
        hrs_result=hr_result,
    )
