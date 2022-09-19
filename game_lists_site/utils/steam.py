import datetime as dt
from sqlite3 import Timestamp

import requests
from bs4 import BeautifulSoup
from flask import current_app
from requests import get
from steam.steamid import SteamID

# from game_lists_site.models import SteamApp, SteamProfile, SteamProfileApp
from game_lists_site.utils.utils import days_delta


def get_steam_id_from_url(url: str):
    print('call get_steam_id_from_url')
    return SteamID.from_url(url)


def get_player_summary(steam_id: int):
    print('call get_player_summary')
    return requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/', params={
        'key': current_app.config['STEAM_API_KEY'],
        'steamids': steam_id
    }).json()['response']['players'][0]


def get_owned_games(steam_id: int):
    print('call get_owned_games')
    return requests.get('http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/', params={
        'key': current_app.config['STEAM_API_KEY'],
        'steamid': steam_id,
        'include_appinfo': True,
        'include_played_free_games': True
    }).json()['response']['games']


def get_app_details(app_id):
    print('call get_appdetails')
    data = requests.get(
        "https://store.steampowered.com/api/appdetails?lang=en_US",
        params={'appids': app_id}).json()
    try:
        if 'data' not in data[list(data.keys())[0]]:
            print(app_id)
            return None
    except AttributeError:
        return None
    return data[list(data.keys())[0]]['data']


def get_app_tags(app_id):
    print('call get_app_tags')
    response = get(f'https://store.steampowered.com/app/{app_id}')
    bs = BeautifulSoup(response.text, "html.parser")
    app_tags = bs.find_all("a", {"class": "app_tag"})
    tags = []
    for tag in app_tags:
        tags.append(tag.text.strip())
    return tags

# def get_profile(profile_id):
#     profile = SteamProfile.get_or_none(SteamProfile.id == profile_id)
#     update = not profile.last_update_time or delta_gt(
#         profile.last_update_time, 1) if profile else False
#     if (profile and update) or (not profile):
#         print('call get_player_summaries')
#         result = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/', params={
#             'key': current_app.config['STEAM_API_KEY'],
#             'steamids': profile_id
#         })
#         print(result.text)
#         result = result.json()
#         if len(result['response']['players']) >= 1:
#             result = result['response']['players'][0]
#         else:
#             result = None
#         if result:
#             profile, _ = SteamProfile.get_or_create(id=profile_id)
#             profile.is_public = result['communityvisibilitystate'] == 3
#             profile.name = result['personaname']
#             profile.url = result['profileurl']
#             profile.avatar_url = result['avatarfull']
#             profile.time_created = dt.datetime.fromtimestamp(
#                 result['timecreated']) if 'timecreated' in result else dt.datetime.now()
#             profile.last_update_time = dt.datetime.now()
#             profile.save()
#     return profile


# def get_profile_apps(profile_id):
#     profile = SteamProfile.get_or_none(SteamProfile.id == profile_id)
#     if not profile:
#         return None
#     update = not profile.last_apps_update_time or delta_gt(
#         profile.last_apps_update_time, 1)
#     if update:
#         query = SteamProfileApp.delete().where(SteamProfileApp.steam_profile == profile)
#         query.execute()

#         print('call get_owned_games')
#         result = requests.get('http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/',
#                               params={
#                                   'key': current_app.config['STEAM_API_KEY'],
#                                   'steamid': profile_id,
#                                   'include_appinfo': True,
#                                   'include_played_free_games': True}).json()
#         if result['response'] and 'games' in result['response']:
#             for r in result['response']['games']:
#                 if r['rtime_last_played'] != 0:
#                     app = SteamApp.get_or_none(SteamApp.id == r['appid'])
#                     if not app:
#                         app = SteamApp.create(id=r['appid'], name=r['name'])
#                     else:
#                         app.name = r['name']
#                     SteamProfileApp.create(steam_profile=profile,
#                                            steam_app=app, playtime=r['playtime_forever'], last_play_time=dt.datetime.fromtimestamp(r['rtime_last_played']))
#     steam_profile_apps = [spa for spa in SteamProfileApp.select().where(
#         SteamProfileApp.steam_profile == profile) if spa.steam_app.is_game]
#     if steam_profile_apps:
#         profile.last_apps_update_time = dt.datetime.now()
#         profile.save()
#     return steam_profile_apps


# def predict_start_date(profile, app):
#     print('call GetPlayerAchievements')
#     result = requests.get('http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/',
#                           params={
#                               'appid': app.id,
#                               'key': current_app.config['STEAM_API_KEY'],
#                               'steamid': profile.id}).json()
#     result = result['playerstats'] if result and 'playerstats' in result else None
#     result = result['achievements'] if result and 'achievements' in result else None
#     timestamps = []
#     if result:
#         [timestamps.append(a['unlocktime'])
#          for a in result if a['unlocktime'] > 0]
#     if timestamps:
#         return dt.datetime.fromtimestamp(min(timestamps))
#     else:
#         return None
