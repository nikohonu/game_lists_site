from flask import Blueprint, render_template, current_app, abort, jsonify

from game_lists_site.db import get_db
#from game_lists_site.utils.steam_api import get_steam_id_from_profile_url
from requests import get

bp = Blueprint('steam', __name__, url_prefix='/steam')

# @bp.route('/get-steam-id/<profile_url_id>', methods=['GET'])
#def get_steam_id(profile_url_id: str):
    # profile_url = f'https://steamcommunity.com/id/{profile_url_id}/'
    # player = Player.get_or_none(Player.profile_url == profile_url)
    # if player:
        #return jsonify(player.id)
    #else:
        #data = steam_api.get_steam_id_from_url(profile_url)
        #if data:
            #player, _ = Player.get_or_create(id=int(data))
            #player.profile_url = profile_url
            #player.save()
            #return jsonify(player.id)
        #else:
            #abort(404)
