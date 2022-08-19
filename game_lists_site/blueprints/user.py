import datetime as dt
import json
import threading

from flask import Blueprint, abort, jsonify, render_template
from flask_peewee.utils import get_object_or_404, object_list
from sklearn.metrics.pairwise import cosine_similarity

from game_lists_site.models import (
    Game,
    GameStatistics,
    Simularity,
    Status,
    System,
    User,
    UserGame,
)
from game_lists_site.utils.steam import (
    get_profile,
    get_profile_apps,
    predict_start_date,
)
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


def predict_score(user: User):
    for user_game in UserGame.select().where(UserGame.user == user):
        pt = user_game.steam_playtime + user_game.other_playtime
        game_statistics = GameStatistics.get_or_none(
            GameStatistics.game == user_game.game)
        if game_statistics:
            median_pt = game_statistics.median_playtime
            if pt > median_pt:
                pt = (pt - median_pt) / (median_pt * 3 - median_pt)
                pt = pt * (1 - 0) + 0
                user_game.predicted_score = min(pt, 1)
            else:
                pt = (pt - 0) / (median_pt - 0)
                pt = pt * (0 + 1) + -1
                user_game.predicted_score = pt
            user_game.save()


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
    predict_score(user)
    user_games = UserGame.select().where(
        UserGame.user == user).order_by(UserGame.steam_playtime.desc())
    return object_list('user/games.html', user_games, username=username, paginate_by=40)


def update_simularity():
    excluded_games = [38, 97, 226, 96]
    users = [user for user in User.select() if len(
        UserGame.select().where(UserGame.user == user)) >= 10]
    game_statistics = [game for game in GameStatistics.select(
    ) if game.game.id not in excluded_games]
    user_vecs = []
    for i, user in enumerate(users):
        print(i)
        predict_score(user)
        user_vec = []
        user_games = UserGame.select().where(UserGame.user == user)
        for game_statistic in game_statistics:
            # user_game = UserGame.get_or_none(
            # UserGame.user == user, UserGame.game == game_statistic.game)
            score = 0
            for ug in user_games:
                if ug.game == game_statistic.game:
                    score = ug.predicted_score
            #score = user_game.predicted_score if user_game else 0
            user_vec.append(score)
        user_vecs.append(user_vec)
    user_vecs = cosine_similarity(user_vecs)
    for user, user_vec in zip(users, user_vecs):
        result = {}
        for u, sim in zip(users, user_vec):
            result[u.id] = sim
        simularity = Simularity.get_or_none(user=user)
        if simularity:
            simularity.delete_instance()
        Simularity.create(user=user, simularities=json.dumps(result))


@bp.route('/<username>/recommendations')
def recommendations(username: str):
    last_update, _ = System.get_or_create(key='Simularity')
    if not last_update.date_time_value or delta_gt(last_update.date_time_value, 1):
        threading.Thread(target=update_simularity).start()
        last_update.date_time_value = dt.datetime.now()
        last_update.save()
    user = get_object_or_404(User, User.username == username)
    simularities = json.loads(Simularity.get_or_none(
        Simularity.user == user).simularities)
    result = {}
    simularities = dict(sorted(simularities.items(),
                        key=lambda item: item[1], reverse=True))
    for i, key in enumerate(simularities):
        if i == 0:
            continue
        user = User.get_by_id(key)
        result[User.get_by_id(key)] = simularities[key]
        if i >= 10:
            break
    return render_template('user/recommendations.html', username=username, simularities=result)


@bp.route('/<username>/statistics')
def statistics(username: str):
    return render_template('user/statistics.html', username=username)
