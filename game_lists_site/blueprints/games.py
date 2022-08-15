import numpy as np
from flask import Blueprint, abort, render_template
from flask_peewee.utils import object_list

from game_lists_site.models import GameStatistics, SteamApp, SteamProfileApp
from game_lists_site.utils.steam import get_profile, get_profile_apps

bp = Blueprint('games', __name__, url_prefix='/games')


def update_game_statistics():
    apps = SteamApp.select().where(SteamApp.is_game == True)
    size = len(apps)
    for i, app in enumerate(apps):
        if i % 1000 == 0:
            print(i, size)
        playtimes = np.array([spa.playtime for spa in SteamProfileApp.select().where(
            SteamProfileApp.steam_app == app) if spa.playtime > 0])
        if playtimes.size >= 5:
            gs, _ = GameStatistics.get_or_create(steam_app=app)
            gs.total_playtime = playtimes.sum()
            gs.mean_playtime = playtimes.mean()
            gs.median_playtime = np.median(playtimes)
            gs.max_playtime = max(playtimes)
            gs.min_playtime = playtimes.min()
            gs.player_count = len(playtimes)
            gs.save()


@bp.route('/')
def games():
    # update_game_statistics()
    game_statistics = GameStatistics.select().order_by(
        GameStatistics.player_count.desc())
    return object_list('games/games.html', game_statistics, paginate_by=40)