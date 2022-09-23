import datetime as dt
import json

import numpy as np
import scipy.stats as stats
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
def get_cbr_for_game(game):
    system, _ = System.get_or_create(key='GameCBR')
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        print('get_cbr_for_game')
        corpus = {}
        games = Game.select()
        for g in games:
            features = []
            features += [game_developer.developer.name.replace(
                ' ', '') for game_developer in GameDeveloper.select().where(GameDeveloper.game == g)]
            features += [game_genre.genre.name.replace(
                ' ', '') for game_genre in GameGenre.select().where(GameGenre.game == g)]
            features += [game_tag.tag.name.replace(' ', '')
                         for game_tag in GameTag.select().where(GameTag.game == g)]
            corpus[g] = " ".join(features)
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform(corpus.values())
        cosine_similarity_result = cosine_similarity(X, X)
        for game_a, row in zip(games, cosine_similarity_result):
            reslut = {game.id: value for game, value in zip(
                games, row)}
            game_cbr, _ = GameCBR.get_or_create(game=game_a)
            game_cbr.data = json.dumps(reslut)
            game_cbr.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    return {Game.get_by_id(game_id): value for game_id, value in json.loads(GameCBR.get_or_none(game=game).data).items()}


# Content based recommendationds for user
def get_cbr_for_user(user, max_count=-1):
    if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
        print('get_cbr_for_user')
        user_games_with_score = UserGame.select().where(
            UserGame.user == user).where(UserGame.score > 0)
        games_with_score = [
            user_game.game for user_game in user_games_with_score]
        played_games = [user_game.game for user_game in UserGame.select().where(
            UserGame.user == user).where(UserGame.playtime > 0)]
        games = {}
        for user_game_with_score in user_games_with_score:
            cbr_result = dict(sorted(get_cbr_for_game(
                user_game_with_score.game).items(), key=lambda x: x[1], reverse=True)[0:10])
            for game in cbr_result:
                if (game not in played_games) and (game not in games_with_score):
                    if game.id in games:
                        games[game.id] = max(
                            games[game.id], cbr_result[game] * user_game_with_score.score)
                    else:
                        games[game.id] = cbr_result[game] * \
                            user_game_with_score.score
        user_cbr, _ = UserCBR.get_or_create(user=user)
        user_cbr.data = json.dumps(games)
        user_cbr.save()
        user.last_cbr_update_time = dt.datetime.now()
        user.save()
    data = {Game.get_by_id(game_id): value for game_id, value in json.loads(UserCBR.get_or_none(UserCBR.user == user).data).items()}
    if len(data) > max_count:
        return dict(list(data.items())[:max_count])
    else:
        return data


def get_game_stats(game: Game):
    game_stats = GameStats.get_or_none(GameStats.game == game)
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        game_stats.player_count = len(
            UserGame.select().where(UserGame.game == game).where(UserGame.playtime > 0))
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
