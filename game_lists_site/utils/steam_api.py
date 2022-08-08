from bs4 import BeautifulSoup
from flask import current_app
from requests import get
from steam.steamid import SteamID
from steam.webapi import WebAPI


class SteamAPI:
    @staticmethod
    def get_app_details(app_id):
        print('call get_appdetails')
        response = get(
            "https://store.steampowered.com/api/appdetails",
            params={'appids': app_id})
        return response.json()

    @staticmethod
    def get_app_tags(app_id):
        print('call get_app_tags')
        response = get(f'https://store.steampowered.com/app/{app_id}')
        bs = BeautifulSoup(response.text)
        app_tags = bs.find_all("a", {"class": "app_tag"})
        tags = []
        for tag in app_tags:
            tags.append(tag.text.strip())
        return tags


def get_steam_id_from_url(url: str):
    print('call get_steam_id_from_url')
    return SteamID.from_url(url)


def get_player_summaries(steam_ids):
    print('call get_player_summaries')
    return WebAPI(
        key=current_app.config['STEAM_API_KEY']).ISteamUser.GetPlayerSummaries(
        steamids=steam_ids)


def get_owned_games(steam_id):
    print('call get_owned_games')
    return WebAPI(
        key=current_app.config['STEAM_API_KEY']).IPlayerService.GetOwnedGames(
        steamid=steam_id, appids_filter=[], include_appinfo=True,
        include_free_sub=True, include_played_free_games=True)
