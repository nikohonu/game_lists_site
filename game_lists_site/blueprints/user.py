import datetime as dt
import json
import threading

import numpy as np
from flask import Blueprint, abort, render_template
from flask_peewee.utils import get_object_or_404, object_list
from sklearn import preprocessing
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.models import (Game, Status, System, User, UserGame,
                                    UserSimilarities)
from game_lists_site.utils.steam import (get_profile, get_profile_apps,
                                         predict_start_date)
from game_lists_site.utils.utils import delta_gt

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/<username>')
def user(username: str):
    user = User.get_or_none(username=username)
    if not user:
        abort(404)
    steam_profile = get_profile(user.steam_profile.id)
    steam_profile_apps = sorted(list(get_profile_apps(
        steam_profile.id)), key=lambda x: x.playtime, reverse=True)
    steam_profile_apps = [
        app for app in steam_profile_apps if app.playtime != 0]
    if steam_profile:
        return render_template('user/user.html', username=username,
                               steam_profile=steam_profile, steam_profile_apps=steam_profile_apps)
    else:
        return abort(404)


@bp.route('/<username>/games')
def games(username: str):
    user = get_object_or_404(User, User.username == username)
    status = Status.get_or_none(Status.id == 1)
    if not status:
        status = Status.create(id=1, name='inbox')
    update = not user.last_games_update_time or delta_gt(
        user.last_games_update_time, 1)
    if update:
        for profile_app in get_profile_apps(user.steam_profile.id):
            if profile_app.steam_app.is_game:
                game, _ = Game.get_or_create(steam_app=profile_app.steam_app)
                user_game = UserGame.get_or_none(
                    UserGame.user == user, UserGame.game == game)
                if not user_game:
                    start_date = predict_start_date(
                        profile_app.steam_profile, profile_app.steam_app)
                    end_date = profile_app.last_play_time
                    UserGame.create(user=user, game=game, status=status,
                                    steam_playtime=profile_app.playtime, start_date=start_date, end_date=end_date)
                else:
                    user_game.steam_playtime = profile_app.playtime
                    end_date = profile_app.last_play_time
                    user_game.save()
            user.last_games_update_time = dt.datetime.now()
            user.save()
    user_games = UserGame.select().where(
        UserGame.user == user).order_by(UserGame.steam_playtime.desc())
    return object_list('user/games.html', user_games, username=username, paginate_by=40)


def update_user_similarities():
    games = Game.select()
    users = [user for user in User.select() if len(
        UserGame.select().where(UserGame.user == user)) >= 10]
    game_vecs = []
    for game in games:
        print(game)
        game_vec = {user: 0 for user in users}
        user_games = UserGame.select().where(UserGame.game == game)
        for ug in user_games:
            if ug.user in game_vec:
                game_vec[ug.user] = ug.steam_playtime + ug.other_playtime
        game_vecs.append(preprocessing.normalize([list(game_vec.values())])[0])
    game_vecs = np.array(game_vecs, dtype=np.float32)
    user_vecs = np.flip(np.rot90(game_vecs), 0)
    user_vecs = cosine_similarity(user_vecs)
    for user, user_vec in zip(users, user_vecs):
        result = {}
        for u, sim in zip(users, user_vec):
            result[u.id] = float(sim)
        similarities = UserSimilarities.get_or_none(user=user)
        if similarities:
            similarities.delete_instance(recursive=True)
        UserSimilarities.create(user=user, similarities=json.dumps(result))
    print('OK!')


@bp.route('/<username>/recommendations')
def recommendations(username: str):
    last_update, _ = System.get_or_create(key='UserSimilarities')
    if not last_update.date_time_value or delta_gt(last_update.date_time_value, 1):
        threading.Thread(target=update_user_similarities).start()
        last_update.date_time_value = dt.datetime.now()
        last_update.save()
    user = get_object_or_404(User, User.username == username)
    similarities = UserSimilarities.get_or_none(UserSimilarities.user == user)
    if similarities:
        similarities = {User.get_by_id(key): value for key, value in json.loads(
            similarities.similarities).items()}
        similarities = dict(sorted(similarities.items(),
                                   key=lambda item: item[1], reverse=True)[1:11])
    games = set(
        [user_game.game for user_game in UserGame.select().where(UserGame.user == user)])
    new_games = dict()
    for u in similarities:
        for user_game in UserGame.select().where(UserGame.user == u):
            game = user_game.game
            if game not in games:
                if game in new_games:
                    new_games[game]['total'] += (user_game.steam_playtime +
                                                 user_game.other_playtime) * similarities[u]
                    new_games[game]['count'] += 1
                else:
                    new_games[game] = {
                        'total': user_game.predicted_score * similarities[u],
                        'count': 1,
                    }
    recommendations = {}
    for game in new_games:
        if new_games[game]['count'] > 1 and new_games[game]['count'] <= 5:
            recommendations[game] = {'result': new_games[game]['total'] /
                                     new_games[game]['count'], 'count': new_games[game]['count']}
    recommendations = dict(
        sorted(recommendations.items(), key=lambda item: item[1]['result'], reverse=True)[:10])
    return render_template('user/recommendations.html', username=username, similarities=similarities, recommendations=recommendations)


@ bp.route('/<username>/statistics')
def statistics(username: str):
    return render_template('user/statistics.html', username=username)
