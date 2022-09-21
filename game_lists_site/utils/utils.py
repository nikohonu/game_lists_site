import datetime as dt

import game_lists_site.utils.steam as steam
from game_lists_site.models import (Developer, Game, GameDeveloper, GameGenre,
                                    GameTag, Genre, Tag, System, GameCBR, UserCBR, UserGame, User)
from sklearn.metrics.pairwise import cosine_similarity
import json


from sklearn.feature_extraction.text import CountVectorizer


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
    print('get_cbr_for_game')
    system, _ = System.get_or_create(key='GameCBR')
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
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
def get_cbr_for_user(user, max_count = -1):
    print('get_cbr_for_user')
    if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
        user_games_with_score = UserGame.select().where(UserGame.user == user).where(UserGame.score > 0)
        games_with_score = [user_game.game for user_game in user_games_with_score]
        played_games = [user_game.game for user_game in UserGame.select().where(UserGame.user == user).where(UserGame.playtime > 0)]
        games = {}
        for user_game_with_score in user_games_with_score:
            cbr_result = dict(sorted(get_cbr_for_game(user_game_with_score.game).items(), key=lambda x: x[1], reverse=True)[0:10])
            for game in cbr_result:
                if (game not in played_games) and (game not in games_with_score):
                    if game.id in games:
                        games[game.id] = max(games[game.id], cbr_result[game] * user_game_with_score.score)
                    else:
                        games[game.id] = cbr_result[game] * user_game_with_score.score
        if max_count != -1:
            games = dict(sorted(games.items(), key=lambda x: x[1], reverse=True)[:max_count])
        user_cbr, _ = UserCBR.get_or_create(user=user)
        user_cbr.data = json.dumps(games)
        user_cbr.save()
        user.last_cbr_update_time = dt.datetime.now()
        user.save()
    return {Game.get_by_id(game_id): value for game_id, value in json.loads(UserCBR.get_or_none(UserCBR.user==user).data).items()}