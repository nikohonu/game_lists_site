from time import time

from bs4 import BeautifulSoup
from flask import current_app
from requests import get
from steam.steamid import SteamID
from steam.webapi import WebAPI

from game_lists_site.db import get_db


def get_app_details(app_id):
    print('call get_appdetails')
    response = get(
        "https://store.steampowered.com/api/appdetails",
        params={'appids': app_id})
    return response.json()


def get_app_tags(app_id):
    print('call get_app_tags')
    response = get(f'https://store.steampowered.com/app/{app_id}')
    bs = BeautifulSoup(response.text)
    app_tags = bs.find_all("a", {"class": "app_tag"})
    tags = []
    for tag in app_tags:
        tags.append(tag.text.strip())
    return tags


def get_profile_id_from_url(url: str):
    print('call get_steam_id_from_url')
    return SteamID.from_url(url)


def get_owned_games(profile_id):
    print('call get_owned_games')
    return WebAPI(
        key=current_app.config['STEAM_API_KEY']).IPlayerService.GetOwnedGames(
        steamid=profile_id, appids_filter=[], include_appinfo=True,
        include_free_sub=True, include_played_free_games=True, language="")


def delta_gt(timestamp, days=1):
    delta = time()-timestamp
    second_in_days = 86400 * days
    return delta > second_in_days


def get_profile(profile_id):
    db = get_db()

    def get_from_db(db, profile_id):
        result = db.execute(
            'SELECT * FROM steam_profile WHERE id = ?', (profile_id,)).fetchone()
        if result:
            return {
                'id': result[0],
                'is_public': bool(result[1]),
                'name': result[2],
                'url': result[3],
                'avatar_url': result[4],
                'time_created': result[5],
                'last_update_time': result[6],
                'last_app_update_time': result[7]}
        else:
            return None

    def get_from_steam_api(profile_id):
        print('call get_player_summaries')
        web_api = WebAPI(key=current_app.config['STEAM_API_KEY'])
        result = web_api.ISteamUser.GetPlayerSummaries(steamids=profile_id)
        result = result['response']['players'][0]
        if result:
            return {
                'id': result['steamid'],
                'is_public': result['communityvisibilitystate'] == 3,
                'name': result['personaname'],
                'url': result['profileurl'],
                'avatar_url': result['avatarfull'],
                'time_created': result['timecreated'],
                'last_update_time': int(time()),
                'last_app_update_time': None}
        else:
            return None

    profile = get_from_db(db, profile_id)
    update = False
    if profile:
        last_update_time = profile['last_update_time']
        update = not last_update_time or delta_gt(last_update_time, 1)
    if (profile and update) or (not profile):
        profile = get_from_steam_api(profile_id)
        if update and profile:
            db.execute(
                'UPDATE steam_profile SET is_public = ?, name = ?, url = ?, '
                'avatar_url = ?, time_created = ?, last_update_time = ? '
                'WHERE id = ?',
                list(profile.values())[1:6] + [int(time()), profile_id])
        elif profile:
             db.execute(
                'INSERT INTO steam_profile (id, is_public, name, url, '
                'avatar_url, time_created, last_update_time, '
                'last_app_update_time) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                list(profile.values()))
        db.commit()
    return profile


def get_profile_games(profile_id):
    db = get_db()
    games = []
    return games
