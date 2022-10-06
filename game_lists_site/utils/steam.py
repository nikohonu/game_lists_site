import datetime as dt

import requests
from bs4 import BeautifulSoup
from flask import current_app
from requests import get
from steam.steamid import SteamID


def days_delta(datetime):
    current_date = dt.datetime.now()
    return (current_date - datetime).days


def get_steam_id_from_url(url: str):
    print("call get_steam_id_from_url")
    return SteamID.from_url(url)


def get_player_summary(steam_id: int):
    print("call get_player_summary")
    r = requests.get(
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
        params={"key": current_app.config["STEAM_API_KEY"], "steamids": steam_id},
    ).json()["response"]["players"]
    if len(r):
        return r[0]
    else:
        return None


def get_owned_games(steam_id: int):
    print("call get_owned_games")
    return requests.get(
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
        params={
            "key": current_app.config["STEAM_API_KEY"],
            "steamid": steam_id,
            "include_appinfo": True,
            "include_played_free_games": True,
        },
    ).json()["response"]["games"]


def get_app_details(app_id):
    print("call get_appdetails")
    data = requests.get(
        "https://store.steampowered.com/api/appdetails",
        params={"appids": app_id, "l": "english"},
    ).json()
    try:
        if "data" not in data[list(data.keys())[0]]:
            print(app_id)
            return None
    except AttributeError:
        return None
    return data[list(data.keys())[0]]["data"]


def get_app_tags(app_id):
    print("call get_app_tags")
    response = get(f"https://store.steampowered.com/app/{app_id}")
    bs = BeautifulSoup(response.text, "html.parser")
    app_tags = bs.find_all("a", {"class": "app_tag"})
    tags = []
    for tag in app_tags:
        tags.append(tag.text.strip())
    return tags
