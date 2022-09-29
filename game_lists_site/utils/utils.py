import datetime as dt
import json

import numpy as np
import scipy.stats as stats
from operator import itemgetter
from sklearn import preprocessing
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import game_lists_site.utils.steam as steam
from game_lists_site.models import (Developer, Game, GameCBR, GameDeveloper,
                                    GameGenre, GameStats, GameTag, Genre,
                                    System, Tag, User, UserCBR, UserGame,
                                    UserMBCF)


def days_delta(datetime):
    current_date = dt.datetime.now()
    return (current_date - datetime).days


def get_game(game_id: int):
    game = Game.get_or_none(Game.id == game_id)
    if not game or not game.last_update_time or days_delta(game.last_update_time) >= 7:
        print(game)
        if game:
            print(game.last_update_time)
        data = steam.get_app_details(game_id)
        if not data:
            return None
        if not game:
            game, _ = Game.get_or_create(
                id=data['steam_appid'], name=data['name'])
        game.description = data.get('about_the_game', '')
        if data['release_date']['date']:
            try:
                game.release_date = dt.datetime.strptime(
                    data['release_date']['date'], "%d %b, %Y").date()
            except:
                game.release_date = None
        game.image_url = data['header_image']
        # clear
        q = GameDeveloper.delete().where(GameDeveloper.game == game)
        q.execute()
        q = GameGenre.delete().where(GameGenre.game == game)
        q.execute()
        q = GameTag.delete().where(GameTag.game == game)
        q.execute()
        # clear end
        for developer_name in data.get('developers', []):
            developer, _ = Developer.get_or_create(name=developer_name)
            GameDeveloper.get_or_create(game=game, developer=developer)
        for genre_dict in data.get('genres', []):
            genre, _ = Genre.get_or_create(id=genre_dict['id'],
                                           name=genre_dict['description'])
            GameGenre.get_or_create(game=game, genre=genre)
        for tag_name in steam.get_app_tags(game.id):
            tag, _ = Tag.get_or_create(name=tag_name)
            GameTag.get_or_create(game=game, tag=tag)
        game.last_update_time = dt.datetime.now()
        game.save()
    return game


# Content based recommendationds for game
def get_cbr_for_game(game, result_count = 9):
    system, _ = System.get_or_create(key='GameCBR')
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        print('get_cbr_for_game')
        corpus = {}
        games = [game for game in Game.select(
        ) if get_game_stats(game).player_count > 16] # min_player_count = 16 is better, because the tests say so
        for game in games:
            corpus[game] = get_game_stats(game).features
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform(corpus.values())
        cosine_similarity_result = cosine_similarity(X, X)
        for game_a, row in zip(games, cosine_similarity_result):
            result = [(game_b.id, value) for game_b, value in zip(games, row) if value >= 0.5]
            result= dict(sorted(result, key=itemgetter(1), reverse=True))
            game_cbr, _ = GameCBR.get_or_create(game=game_a)
            game_cbr.data = json.dumps(result)
            game_cbr.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    game_cbr = GameCBR.get_or_none(game=game)
    if game_cbr:
        data = {Game.get_by_id(game_id): value for game_id, value in json.loads(game_cbr.data).items()}
        if len(data) > result_count + 1:
            return dict(list(data.items())[:result_count+1])
        else:
            return dict(list(data.items())[1:])
    else:
        return []


# Content based recommendationds for user
def get_cbr_for_user(user, result_count=9):
    if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
        print('get_cbr_for_user')
        played_user_games = UserGame.select().where(
            UserGame.user == user).where(UserGame.playtime > 0)
        played_games = [ug.game for ug in played_user_games]
        user_games_with_score = played_user_games.where(UserGame.score != None)
        games_with_score = [ug.game for ug in user_games_with_score]
        result = {}
        for user_game, game_cbr_result in zip(user_games_with_score, [get_cbr_for_game(g, 6) for g in games_with_score]): # best_game_cbr_result_count = 6 is better, because the tests say so
            if game_cbr_result:
                for sim_game in game_cbr_result:
                    if sim_game not in played_games:
                        if sim_game.id not in result:
                            result[sim_game.id] = user_game.score * \
                                game_cbr_result[sim_game]
                        else:
                            result[sim_game.id] += user_game.score * \
                                game_cbr_result[sim_game]
        user_cbr, _ = UserCBR.get_or_create(user=user)
        user_cbr.data = json.dumps(dict(sorted(result.items(), key=lambda x: x[1], reverse=True)))
        user_cbr.save()
        user.last_cbr_update_time = dt.datetime.now()
        user.save()
    data = {Game.get_by_id(game_id): value for game_id, value in json.loads(UserCBR.get_or_none(UserCBR.user == user).data).items()}
    if len(data) > result_count:
        return dict(list(data.items())[:result_count])
    else:
        return data


def get_game_stats(game: Game):
    game_stats = GameStats.get_or_none(GameStats.game == game)
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        game_stats.player_count = len(
            UserGame.select().where(UserGame.game == game).where(UserGame.playtime > 0))
        # features
        features = []
        features += [game_developer.developer.name.replace(
            " ", "") for game_developer in GameDeveloper.select().where(GameDeveloper.game == game)]
        features += [game_genre.genre.name.replace(
            " ", "") for game_genre in GameGenre.select().where(GameGenre.game == game)]
        features += [game_tag.tag.name.replace(' ', '')
                     for game_tag in GameTag.select().where(GameTag.game == game)]
        game_stats.features = " ".join(features)
        # features end
        game_stats.last_update_time = dt.datetime.now()
        game_stats.save()
    return game_stats


def calc_normalized_playtime():
    system, _ = System.get_or_create(key='NormalizedPlaytime')
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        print("calc_normalized_playtime")
        q = (UserGame.update({UserGame.normalized_playtime: None}))
        q.execute()
        games = [game for game in Game.select(
        ) if get_game_stats(game).player_count > 5]
        users = [user for user in User.select()]
        i = 1
        count = len(games)
        for game in games:
            print(i, count)
            user_games = UserGame.select().where(
                UserGame.game == game).where(UserGame.playtime > 0)
            playtimes = [user_game.playtime for user_game in user_games]
            normalized_playtimes = stats.zscore(playtimes)
            for ug, normalized_playtime in zip(user_games, normalized_playtimes):
                ug.normalized_playtime = normalized_playtime
                ug.save()
            i += 1
        i = 1
        count = len(users)
        for user in users:
            print(i, count)
            user_games = [ug for ug in UserGame.select().where(UserGame.user == user) if ug.normalized_playtime != None]
            normalized_playtimes = stats.zscore([user_game.playtime for user_game in user_games])
            for ug, normalized_playtime in zip(user_games, normalized_playtimes):
                ug.normalized_playtime = normalized_playtime
                ug.save()
            i += 1
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
        system.date_time_value = dt.datetime.now()
        system.save()


def get_mbcf_for_user(target_user, max_count=-1):
    system, _ = System.get_or_create(key='UserMBCF')
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        print('get_mbcf_for_user')
        calc_normalized_playtime()
        games = [game for game in Game.select(
        ) if get_game_stats(game).player_count >= 5]
        users = [user for user in User.select() if len(
            UserGame.select().where(UserGame.user == user).where(UserGame.normalized_playtime != None)) >= 5]
        game_vecs = []
        for game in games:
            print(game.id)
            game_vec = {user: 0 for user in users}
            user_games = UserGame.select().where(UserGame.game == game).where(
                UserGame.normalized_playtime != None)
            for ug in user_games:
                if ug.user in game_vec:
                    game_vec[ug.user] = ug.normalized_playtime
            game_vecs.append(list(game_vec.values()))
        game_vecs = np.array(game_vecs, dtype=np.float32)
        user_vecs = np.flip(np.rot90(game_vecs), 0)
        # user_vecs = cosine_similarity(user_vecs)
        user_vecs = np.corrcoef(user_vecs)
        sim_users = {}
        for user, user_vec in zip(users, user_vecs):
            result = {}
            for u, sim in zip(users, user_vec):
                result[u] = float(sim)
            result = dict(
                sorted(result.items(), key=lambda x: x[1], reverse=True)[1:10])
            sim_users[user] = result
        for user_a, sim in sim_users.items():
            played_games = [user_game.game for user_game in UserGame.select().where(
                UserGame.user == user_a).where(UserGame.playtime > 0)]
            games = {}
            for user_b, value in sim.items():
                for user_game in UserGame.select().where(UserGame.user == user_b).where(UserGame.normalized_playtime != None):
                    if user_game.game not in played_games:
                        game = user_game.game
                        # print(user_game, user_game.normalized_playtime, sim)
                        if game.id in games:
                            # games[game.id] = max(
                            # games[game.id], user_game.normalized_playtime * value)
                            games[game.id] += user_game.normalized_playtime * value
                        else:
                            games[game.id] = user_game.normalized_playtime * value
            games = dict(
                sorted(games.items(), key=lambda x: x[1], reverse=True))
            user_mbcf, _ = UserMBCF.get_or_create(user=user_a)
            user_mbcf.data = json.dumps(games)
            user_mbcf.save()
            system.date_time_value = dt.datetime.now()
            system.save()
    data = {Game.get_by_id(game_id): value for game_id, value in json.loads(
        UserMBCF.get_or_none(UserMBCF.user == target_user).data).items()}
    if len(data) > max_count:
        return dict(list(data.items())[:max_count])
    else:
        return data
