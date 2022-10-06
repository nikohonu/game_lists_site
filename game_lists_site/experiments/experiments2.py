import datetime as dt
import json

import scipy.stats as stats

from game_lists_site.models import (
    Game,
    GameDeveloper,
    GameGenre,
    GameStats,
    GameTag,
    System,
    User,
    UserGame,
    UserMBCF,
    user_data_dir,
)


def days_delta(datetime):
    current_date = dt.datetime.now()
    return (current_date - datetime).days


games_stats_data = {gs.game: gs for gs in GameStats.select()}


def get_game_stats(game: Game):
    if game in games_stats_data:
        game_stats = games_stats_data[game]
    else:
        game_stats = None
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        # features
        features = []
        features += [
            game_developer.developer.name.replace(" ", "")
            for game_developer in GameDeveloper.select().where(
                GameDeveloper.game == game
            )
        ]
        features += [
            game_genre.genre.name.replace(" ", "")
            for game_genre in GameGenre.select().where(GameGenre.game == game)
        ]
        features += [
            game_tag.tag.name.replace(" ", "")
            for game_tag in GameTag.select().where(GameTag.game == game)
        ]
        game_stats.features = " ".join(features)
        # features end
        game_stats.update(
            {
                Game.player_count: len(
                    UserGame.select()
                    .where(UserGame.game == game)
                    .where(UserGame.playtime > 0)
                ),
                Game.features: " ".join(features),
                Game.last_update_time: dt.datetime.now(),
            }
        )
        games_stats_data[game] = game_stats
    return game_stats


def get_normalized_playtimes():
    system, _ = System.get_or_create(key="NormalizedPlaytime")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        q = UserGame.update({UserGame.normalized_playtime: None})
        q.execute()
        games = [
            game for game in Game.select() if get_game_stats(game).player_count > 5
        ]
        # users = [user for user in User.select()]
        result = {}
        for game in games:
            user_games = (
                UserGame.select()
                .where(UserGame.game == game)
                .where(UserGame.playtime > 0)
            )
            playtimes = [user_game.playtime for user_game in user_games]
            normalized_playtimes = stats.zscore(playtimes)
            result |= {
                (ug.user.id, ug.game.id): normalized_playtime
                for ug, normalized_playtime in zip(user_games, normalized_playtimes)
            }
        system.date_time_value = dt.datetime.now()
        system.save()
        with (user_data_dir / "normalized_playtimes.json").open("w") as data_file:
            json.dump(list(result), data_file)
        return result
        # for ug, normalized_playtime in zip(user_games, normalized_playtimes):
        # ug.update({UserGame.normalized_playtime: normalized_playtime}).execute()
        # count = len(users)
        # for user in users:
        #     print(i, count)
        #     user_games = [ug for ug in UserGame.select().where(UserGame.user == user) if ug.normalized_playtime != None]
        #     normalized_playtimes = stats.zscore([user_game.playtime for user_game in user_games])
        #     for ug, normalized_playtime in zip(user_games, normalized_playtimes):
        #         ug.normalized_playtime = normalized_playtime
        #         ug.save()
        #     i += 1
        # for user in users:
        #     if len(user_games) >= 5:
        #         max_np = max([ug.normalized_playtime for ug in user_games if normalized_playtime])
        #         min_np = min([ug.normalized_playtime for ug in user_games if normalized_playtime])
        #         for user_game in user_games:
        #             if normalized_playtime >= 0:
        #                 user_game.normalized_playtime = (user_game.normalized_playtime / max_np) * 5 + 5
        #             if normalized_playtime < 0:
        #                 min_np = abs(min_np)
        #                 user_game.normalized_playtime = ((user_game.normalized_playtime + min_np) / min_np) * 5
        #             user_game.save()
        #     else:
        #         for user_game in user_games:
        #             user_game.normalized_playtime = None
        #             user_game.save()

    else:
        with (user_data_dir / "normalized_playtimes.json").open() as data_file:
            result = json.load(data_file)
        return result


def get_mbcf_for_user(target_user, max_count=-1):
    system, _ = System.get_or_create(key="UserMBCF")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        normalized_playtimes = get_normalized_playtimes()
        games = [
            game for game in Game.select() if get_game_stats(game).player_count >= 5
        ]
        users = [
            user
            for user in User.select()
            if len([key for key in normalized_playtimes if key[0] == user.id]) >= 5
        ]
        print(len(users))
        game_vecs = []
        for game in games:
            game_vec = {user: 0 for user in users}
            user_games = (
                UserGame.select()
                .where(UserGame.game == game)
                .where(UserGame.playtime != None)
            )
            for ug in user_games:
                if (
                    ug.user in game_vec
                    and (ug.user.id, ug.game.id) in normalized_playtimes
                ):
                    game_vec[ug.user] = normalized_playtimes[(ug.user.id, ug.game.id)]
        #             game_vecs.append(list(game_vec.values()))
        #         game_vecs = np.array(game_vecs, dtype=np.float32)
        #         user_vecs = np.flip(np.rot90(game_vecs), 0)
        #         # user_vecs = cosine_similarity(user_vecs)
        #         user_vecs = np.corrcoef(user_vecs)
        #         # -- find sim user --
        #         sim_users = {}
        #         for user, user_vec in zip(users, user_vecs):
        #             result = {}
        #             for u, sim in zip(users, user_vec):
        #                 result[u] = float(sim)
        #             result = dict(
        #                 sorted(result.items(), key=lambda x: x[1], reverse=True)[1:10])
        #             sim_users[user] = result
        #         i = 1
        #         m = len(sim_users)
        #         print('a')
        #         global_user_game = list(UserGame.select())
        #         print('b')
        #         for user_a, sim in sim_users.items():
        #             # if (i % 10 == 0):
        #             print(i, '/', m)
        #             i += 1
        #             # played_games = [user_game.game for user_game in UserGame.select().where(
        #             #     UserGame.user == user_a).where(UserGame.playtime > 0)]
        #             played_games = [user_game.game for user_game in global_user_game
        #                             if user_game.user == user_a and user_game.playtime]
        #             games = {}
        #             for user_b, value in sim.items():
        #                 # for user_game in UserGame.select().where(UserGame.user == user_b).where(UserGame.playtime != None):
        #                 for user_game in [user_game for user_game in global_user_game
        #                             if user_game.user == user_b and user_game.playtime]:
        #                     if user_game.game not in played_games and (game, user_b.id) in normalized_playtimes:
        #                         game = user_game.game
        #                         # print(user_game, user_game.normalized_playtime, sim)
        #                         if game.id in games:
        #                             # games[game.id] = max(
        #                             # games[game.id], user_game.normalized_playtime * value)
        #                             # games[game.id] += user_game.normalized_playtime * value
        #                             games[game.id] += normalized_playtimes[(
        #                                 game, user_b.id)] * value
        #                         else:
        #                             games[game.id] = normalized_playtimes[(
        #                                 game, user_b.id)] * value
        #             games = dict(
        #                 sorted(games.items(), key=lambda x: x[1], reverse=True))
        #             user_mbcf, _ = UserMBCF.get_or_create(user=user_a)
        #             user_mbcf.data = json.dumps(games)
        #             user_mbcf.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    data = {
        Game.get_by_id(game_id): value
        for game_id, value in json.loads(
            UserMBCF.get_or_none(UserMBCF.user == target_user).data
        ).items()
    }
    if len(data) > max_count:
        return dict(list(data.items())[:max_count])
    else:
        return data


def do_test(users):
    for user in users:
        print(user.username)
        print(get_mbcf_for_user(user, 9))
    # for key in ['NormalizedPlaytime', 'UserMBCF']:
    for key in ["UserMBCF"]:
        system = System.get(key=key)
        system.date_time_value = None
        system.save()
    # played_user_games = UserGame.select().where(
    # UserGame.user == user).where(UserGame.playtime > 0)
    # user_games_with_score = played_user_games.where(UserGame.score != None)
    # quantile = np.quantile(
    #     [ug.last_played for ug in user_games_with_score], 0.90)
    # input_user_games = [
    #     ug for ug in user_games_with_score if ug.last_played <= quantile]
    # input_games = [ug.game for ug in input_user_games]
    # check_user_games = [
    #     ug for ug in user_games_with_score if ug.last_played > quantile]
    # played_games = set()
    # for ug in input_user_games:
    #     played_games.add(ug.game)
    # for ug in played_user_games:
    #     if ug not in check_user_games:
    #         played_games.add(ug.game)
    # played_games = list(played_games)
    # result = get_mbcf_for_user(user)

    # accuracy = 0
    # for ug in check_user_games:
    #     if ug.game in result:
    #         accuracy += 1
    # return accuracy/len(check_user_games)
    # return accuracy # temp


def main():
    users = [
        User.get_by_id(user_id)
        for user_id in [
            76561198083927294,
            76561198091812571,
            76561198094109207,
            76561198394079733,
        ]
    ]
    do_test(users)
    # print(get_normalized_playtimes())
    # accuracies = []
    # for user_id in user_ids:
    #     accuracies.append(do_test(user_id))
    # accuracy = np.average(accuracies)
    # print('accuracy:' + str(accuracy))


if __name__ == "__main__":
    main()
