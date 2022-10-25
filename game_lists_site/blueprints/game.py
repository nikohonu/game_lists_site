from bs4 import BeautifulSoup
from flask import Blueprint, abort, render_template

from game_lists_site.algorithms.game import (
    update_cbr_for_game,
    update_hr_for_games,
    update_mbcf_for_games,
)
from game_lists_site.models import (
    Developer,
    Game,
    GameDeveloper,
    GameGenre,
    GameTag,
    Genre,
    Tag,
)
from game_lists_site.utilities import get_readable_result_for_games, update_game

bp = Blueprint("game", __name__, url_prefix="/game")


@bp.route("<game_id>/<game_name>")
def game(game_id, game_name):
    if not update_game(game_id):
        abort(404)
    game = Game.get_by_id(game_id)
    developers = [
        d.name
        for d in Developer.select(Developer.name)
        .join(GameDeveloper)
        .where(GameDeveloper.game == game)
    ]
    genres = [
        g.name
        for g in Genre.select(Genre.name).join(GameGenre).where(GameGenre.game == game)
    ]
    tags = [
        t.name for t in Tag.select(Tag.name).join(GameTag).where(GameTag.game == game)
    ]
    short_description = BeautifulSoup(game.description, "html.parser").get_text(
        separator=" "
    )
    short_description = short_description[: min(500, len(short_description))] if short_description else ""
    update_cbr_for_game()
    update_mbcf_for_games()
    update_hr_for_games()
    cbr_result = get_readable_result_for_games(game.cbr, 9)
    mbcf_result = get_readable_result_for_games(game.mbcf, 9)
    hr_result = get_readable_result_for_games(game.hr, 9)
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
