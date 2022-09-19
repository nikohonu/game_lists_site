import datetime as dt

import game_lists_site.utils.steam as steam
from game_lists_site.models import (Developer, Game, GameDeveloper, GameGenre,
                                    GameTag, Genre, Tag)


def days_delta(datetime):
    current_date = dt.datetime.now()
    return (current_date - datetime).days


def get_game(game_id: int):
    game = Game.get_or_none(Game.id == game_id)
    if not game or not game.last_update_time or days_delta(game.last_update_time) >= 7:
        data = steam.get_app_details(game_id)
        if not data:
            return None
        if not game:
            game, _ = Game.get_or_create(
                id=data['steam_appid'], name=data['name'])
        game.description = data.get('about_the_game', '')
        if data['release_date']['date']:
            game.release_date = dt.datetime.strptime(
                data['release_date']['date'], "%d %b, %Y").date()
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
