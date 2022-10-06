from flask import Blueprint

bp = Blueprint("games", __name__, url_prefix="/games")


# def update_game_statistics():
# games = Game.select()
# size = len(games)
# for i, game in enumerate(games):
#     if i % 1000 == 0:
#         print(i, size)
#     playtimes = np.array(
#         [
#             spa.playtime
#             for spa in SteamProfileApp.select().where(
#                 SteamProfileApp.steam_app == game.steam_app
#             )
#             if spa.playtime > 0
#         ]
#     )
#     if playtimes.size >= 5:
#         gs, _ = GameStatistics.get_or_create(game=game)
#         gs.total_playtime = playtimes.sum()
#         gs.mean_playtime = playtimes.mean()
#         gs.median_playtime = np.median(playtimes)
#         gs.max_playtime = max(playtimes)
#         gs.min_playtime = playtimes.min()
#         gs.player_count = len(playtimes)
#         gs.save()


@bp.route("/")
def games():
    pass
    # last_update, _ = System.get_or_create(key="GameStatistics")
    # if not last_update.date_time_value or days_delta(last_update.date_time_value, 1):
    #     threading.Thread(target=update_game_statistics).start()
    #     last_update.date_time_value = datetime.now()
    #     last_update.save()
    # game_statistics = GameStatistics.select().order_by(
    #     GameStatistics.player_count.desc()
    # )
    # return object_list("games/games.html", game_statistics, paginate_by=40)
