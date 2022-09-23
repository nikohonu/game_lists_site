import datetime as dt
import json
import re
import threading

import numpy as np
from bs4 import BeautifulSoup
from flask import Blueprint, abort, jsonify, render_template
from flask_peewee.utils import get_object_or_404
from sklearn import preprocessing

import game_lists_site.utils.steam as steam
from game_lists_site.models import (Developer, Game, GameCBR, GameDeveloper,
                                    GameGenre, GameTag, Genre, System, Tag)
from game_lists_site.utils.utils import days_delta, get_cbr_for_game, get_game

bp = Blueprint('game', __name__, url_prefix='/game')


# def update_game_similarities():
#     games = [game for game in Game.select() if len(
#         UserGame.select().where(UserGame.game == game)) >= 5]
#     # users = [user for user in User.select() if len(
#     # UserGame.select().where(UserGame.user == user)) >= 5]
#     users = User.select()
#     game_vecs = []
#     print(len(games), len(users))
#     for game in games:
#         print(game)
#         game_vec = {user: 0 for user in users}
#         user_games = UserGame.select().where(UserGame.game == game)
#         for ug in user_games:
#             if ug.user in game_vec:
#                 game_vec[ug.user] = ug.steam_playtime + ug.other_playtime
#         game_vecs.append(preprocessing.normalize([list(game_vec.values())])[0])
#     game_vecs = np.array(game_vecs, dtype=np.float32)
#     game_vecs = np.corrcoef(game_vecs)
#     for game, game_vec in zip(games, game_vecs):
#         result = {}
#         for g, sim in zip(games, game_vec):
#             result[g.id] = sim
#         similarities = GameSimilarities.get_or_none(game=game)
#         if similarities:
#             similarities.delete_instance(recursive=True)
#         GameSimilarities.create(game=game, similarities=json.dumps(result))
#     print('ok')


@bp.route('<game_id>/<game_name>')
def game(game_id, game_name):
    game = get_game(game_id)
    if not game:
        abort(404)
    developers = [gd.developer.name for gd in GameDeveloper.select().where(
        GameDeveloper.game == game)]
    genres = [gg.genre.name for gg in GameGenre.select().where(
        GameGenre.game == game)]
    tags = [gt.tag.name for gt in GameTag.select().where(
        GameTag.game == game)]
    short_description = BeautifulSoup(
        game.description, "html.parser").get_text(separator=' ')
    short_description = short_description[:min(500, len(short_description))]
    cbr_result = get_cbr_for_game(game)
    cbr_result = sorted(cbr_result, key=cbr_result.get, reverse=True)[1:10]
    return render_template('game.html', game=game, developers=developers, genres=genres, tags=tags, short_description=short_description, cbr_result=cbr_result)
    # last_update, _ = System.get_or_create(key='GameSimilarities')
    # if not last_update.date_time_value or days_delta(last_update.date_time_value, 1):
    #     threading.Thread(target=update_game_similarities).start()
    #     last_update.date_time_value = dt.datetime.now()
    #     last_update.save()
    # game = get_object_or_404(Game, Game.id == game_id)
    # similarities = GameSimilarities.get_or_none(GameSimilarities.game == game)
    # if similarities:
    #     similarities = {Game.get_by_id(key): value for key, value in json.loads(
    #         similarities.similarities).items()}
    # similarities = dict(sorted(similarities.items(),
    #                     key=lambda item: item[1], reverse=True)[1:11])
    # return render_template('game.html', game=game, similarities=similarities)
