import datetime as dt
import json
import threading

import numpy as np
from flask import Blueprint, render_template
from flask_peewee.utils import get_object_or_404
from sklearn import preprocessing

from game_lists_site.models import (Game, GameSimilarities, System, User,
                                    UserGame)
from game_lists_site.utils.utils import delta_gt

bp = Blueprint('game', __name__, url_prefix='/game')


def update_game_similarities():
    games = [game for game in Game.select() if len(
        UserGame.select().where(UserGame.game == game)) >= 5]
    # users = [user for user in User.select() if len(
    # UserGame.select().where(UserGame.user == user)) >= 5]
    users = User.select()
    game_vecs = []
    print(len(games), len(users))
    for game in games:
        print(game)
        game_vec = {user: 0 for user in users}
        user_games = UserGame.select().where(UserGame.game == game)
        for ug in user_games:
            if ug.user in game_vec:
                game_vec[ug.user] = ug.steam_playtime + ug.other_playtime
        game_vecs.append(preprocessing.normalize([list(game_vec.values())])[0])
    game_vecs = np.array(game_vecs, dtype=np.float32)
    game_vecs = np.corrcoef(game_vecs)
    for game, game_vec in zip(games, game_vecs):
        result = {}
        for g, sim in zip(games, game_vec):
            result[g.id] = sim
        similarities = GameSimilarities.get_or_none(game=game)
        if similarities:
            similarities.delete_instance(recursive=True)
        GameSimilarities.create(game=game, similarities=json.dumps(result))


@bp.route('<game_id>/<game_name>')
def game(game_id, game_name):
    last_update, _ = System.get_or_create(key='GameSimilarities')
    if not last_update.date_time_value or delta_gt(last_update.date_time_value, 1):
        threading.Thread(target=update_game_similarities).start()
        last_update.date_time_value = dt.datetime.now()
        last_update.save()
    game = get_object_or_404(Game, Game.id == game_id)
    similarities = GameSimilarities.get_or_none(GameSimilarities.game == game)
    if similarities:
        similarities = {Game.get_by_id(key): value for key, value in json.loads(
            similarities.similarities).items()}
    similarities = dict(sorted(similarities.items(),
                        key=lambda item: item[1], reverse=True)[1:11])
    return render_template('game.html', game=game, similarities=similarities)