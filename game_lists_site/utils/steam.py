import datetime as dt
from sqlite3 import Timestamp

import requests
from bs4 import BeautifulSoup
from flask import current_app
from requests import get
from steam.steamid import SteamID
from steam.webapi import WebAPI

from game_lists_site.models import SteamApp, SteamProfile, SteamProfileApp
from game_lists_site.utils.utils import delta_gt


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


def get_profile(profile_id):
    profile = SteamProfile.get_or_none(SteamProfile.id == profile_id)
    update = not profile.last_update_time or delta_gt(
        profile.last_update_time, 1) if profile else False
    if (profile and update) or (not profile):
        print('call get_player_summaries')
        web_api = WebAPI(key=current_app.config['STEAM_API_KEY'])
        result = web_api.ISteamUser.GetPlayerSummaries(steamids=profile_id)
        result = result['response']['players'][0]
        if result:
            profile, _ = SteamProfile.get_or_create(id=profile_id)
            profile.is_public = result['communityvisibilitystate'] == 3
            profile.name = result['personaname']
            profile.url = result['profileurl']
            profile.avatar_url = result['avatarfull']
            profile.time_created = dt.datetime.fromtimestamp(
                result['timecreated'])
            profile.last_update_time = dt.datetime.now()
            profile.save()
    return profile


def get_profile_apps(profile_id):
    profile = SteamProfile.get_or_none(SteamProfile.id == profile_id)
    if not profile:
        return None
    update = not profile.last_apps_update_time or delta_gt(
        profile.last_apps_update_time, 1)
    if update:
        query = SteamProfileApp.delete().where(SteamProfileApp.steam_profile == profile)
        query.execute()
        profile.last_apps_update_time = dt.datetime.now()
        profile.save()
        print('call get_owned_games')
        web_api = WebAPI(key=current_app.config['STEAM_API_KEY'])
        result = web_api.IPlayerService.GetOwnedGames(
            steamid=profile_id, appids_filter=[], include_appinfo=True,
            include_free_sub=True, include_played_free_games=True, language="")
        if result['response']:
            for r in result['response']['games']:
                app = SteamApp.get_or_none(SteamApp.id == r['appid'])
                if not app:
                    app = SteamApp.create(id=r['appid'], name=r['name'])
                else:
                    app.name = r['name']
                SteamProfileApp.create(steam_profile=profile,
                                       steam_app=app, playtime=r['playtime_forever'])
    return [spa for spa in SteamProfileApp.select().where(SteamProfileApp.steam_profile == profile) if spa.steam_app.is_game]


def predict_start_and_end_dates(profile, app):
    print('call GetPlayerAchievements')
    result = requests.get('http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/',
                          params={
                              'appid': app.id,
                              'key': current_app.config['STEAM_API_KEY'],
                              'steamid': profile.id}).json()
    result = result['playerstats'] if result and 'playerstats' in result else None
    result = result['achievements'] if result and 'achievements' in result else None
    timestamps = []
    if result:
        [timestamps.append(a['unlocktime'])
         for a in result if a['unlocktime'] > 0]
    start = None
    end = None
    if len(timestamps) >= 2:
        start = min(timestamps)
        end = max(timestamps)
    elif len(timestamps) == 1:
        start = end = timestamps[0]
    print(start, end, timestamps)
    start_date = dt.datetime.fromtimestamp(start) if start else None
    end_date = dt.datetime.fromtimestamp(end) if end else None
    return (start_date, end_date)
