import datetime as dt

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import torch
import torch.nn as nn
import torch.nn.functional as F

from game_lists_site.algorithms.game import update_cbr_for_game
from game_lists_site.models import Game, System, User, UserGame, db, user_data_dir
from game_lists_site.utilities import (
    ParametersManager,
    days_delta,
    get_game_vecs,
    get_normalized_playtimes,
    get_readable_result_for_games,
    merge_dicts,
    normalize_dict,
    get_game_vecs,
    slice_dict,
)


def update_cbr_for_user(user, **current_parameters):
    p = ParametersManager(
        "cbr_for_user",
        current_parameters,
        {
            "min_player_count": 19,
            "cbr_for_game_result_count": 3,
            "max_game": 16,
        },
    )
    if p.is_diff_last_current():
        q = User.update({User.cbr_update_time:None}).where(User.cbr_update_time != None).execute()
    if days_delta(User.get_by_id(user.id).cbr_update_time) >= 1 or not user.cbr:
        # print(f'update cbr for "{user.username}"')
        update_cbr_for_game(min_player_count=p["min_player_count"])
        user.cbr = None
        last_played = np.quantile(
            [
                ug.last_played
                for ug in UserGame.select(UserGame.last_played).where(
                    (UserGame.user == user) & (UserGame.playtime > 0)
                )
            ],
            0.05,
        )
        played_games = (
            Game.select(Game.id, Game.cbr, UserGame.score)
            .join(UserGame)
            .where(
                (UserGame.user == user)
                & (UserGame.playtime > 0)
                & (UserGame.last_played >= last_played)
            )
        )
        games_with_score = played_games.where((UserGame.score > 0) & (Game.cbr != None))
        # use normalized playtimes if not enough games with score
        if games_with_score.count() < 8:
            users_games_playtimes = get_normalized_playtimes(
                True,
                min_player_count=p["min_player_count"],
                zscore=False,
            )
            user_games_playtimes = (
                users_games_playtimes[str(user.id)]
                if str(user.id) in users_games_playtimes
                else []
            )
            result = []
            for game in played_games:
                if str(game.id) in user_games_playtimes.keys():
                    if game.cbr:
                        result.append(
                            {
                                "id": game.id,
                                "cbr": game.cbr,
                                "score": user_games_playtimes[str(game.id)],
                            }
                        )
                games_with_score = result
        # else use score
        else:
            games_with_score = games_with_score.dicts()
        games_with_score = sorted(
            games_with_score, key=lambda x: x["score"], reverse=True
        )[: p["max_game"]]
        # calc result
        result = []
        for game_a_dict in games_with_score:
            result.append(
                {
                    key: value * game_a_dict["score"]
                    for key, value in list(game_a_dict["cbr"].items())[
                        1 : p["cbr_for_game_result_count"] + 1
                    ]
                }
            )
        result = {
            str(game.id): value
            for game, value in get_readable_result_for_games(
                merge_dicts(result)
            ).items()
            if game not in played_games and game.rating >= 7
        }
        user.cbr = result
        user.cbr_update_time = dt.datetime.now()
        user.save()


def update_similar_users(**current_parameters):
    p = ParametersManager(
        "similar_users",
        current_parameters,
        {"min_game_count": 10, "min_player_count": 10},
    )
    system, _ = System.get_or_create(key="similar_users")
    if days_delta(system.date_time) > 15 or p.is_diff_last_current():
        print("update similar users")
        _, user_ids, game_vecs = get_game_vecs(
            p["min_player_count"], p["min_game_count"]
        )
        user_vecs = np.flip(np.rot90(game_vecs), 0)
        users = [User.get_by_id(user_id) for user_id in user_ids]
        user_vecs = np.corrcoef(user_vecs)
        for user_a, row in zip(users, user_vecs):
            user_a.similar_users = dict(
                sorted(
                    [
                        (str(user_id_b), value)
                        for user_id_b, value in zip(user_ids, row)
                    ],
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
        User.bulk_update(users, [User.similar_users])
        system.date_time = dt.datetime.now()
        system.save()


def update_mbcf_for_user(user, **current_parameters):
    p = ParametersManager(
        "mbcf_for_user",
        current_parameters,
        {
            "sim_user_count": 10,
            "min_player_count": 10,
            "min_game_count": 10,
            "max_game": 10,
        },
    )
    if p.is_diff_last_current():
        q = User.update({User.mbcf_update_time:None}).where(User.mbcf_update_time != None).execute()
    if days_delta(User.get_by_id(user.id).mbcf_update_time) >= 1 or not user.mbcf:
        update_similar_users(min_game_count=p["min_game_count"], min_player_count=p["min_player_count"])
        if not user.similar_users:
            print("Fuck")
            return
        last_played = np.quantile(
            [
                ug.last_played
                for ug in UserGame.select(UserGame.last_played).where(
                    (UserGame.user == user) & (UserGame.playtime > 0)
                )
            ],
            0.05,
        )
        played_games = (
            Game.select(Game.id, Game.cbr, UserGame.score)
            .join(UserGame)
            .where(
                (UserGame.user == user)
                & (UserGame.playtime > 0)
                & (UserGame.last_played >= last_played)
            )
        )
        normalized_playtimes = get_normalized_playtimes(
            True, min_player_count=p["min_player_count"], zscore=False
        )
        result = []
        similar_users = slice_dict(user.similar_users, 1, p["sim_user_count"] + 1)
        for user_id, coef in similar_users.items():
            if user_id in normalized_playtimes:
                result.append(
                    {
                        key: value * coef
                        for key, value in sorted(
                            list(normalized_playtimes[user_id].items()),
                            key=lambda x: x[1],
                            reverse=True,
                        )[: p["max_game"]]
                    }
                )
        user.mbcf = {
            str(game.id): value
            for game, value in get_readable_result_for_games(
                merge_dicts(result)
            ).items()
            if game not in played_games and game.rating >= 7
        }
        user.mbcf_update_time = dt.datetime.now()
        user.save()


class MF(nn.Module):
    def __init__(self, num_users, num_items, emb_size=100):
        super(MF, self).__init__()
        self.user_emb = nn.Embedding(num_users, emb_size)
        self.item_emb = nn.Embedding(num_items, emb_size)

    def forward(self, u, v):
        U = self.user_emb(u)
        V = self.item_emb(v)
        return (U * V).sum(1)


def update_mobcf(**current_parameters):
    p = ParametersManager(
        "mobcf",
        current_parameters,
        {"min_player_count": 10, "min_game_count": 10, "zscore": True},
    )
    system, _ = System.get_or_create(key="mobcf_for_user")
    if days_delta(system.date_time) >= 1 or p.is_diff_last_current():
        print("update mobcf")
        User.update({User.mobcf: None}).execute()
        normalized_playtimes = get_normalized_playtimes(
            True, min_player_count=p["min_player_count"], zscore=p["zscore"]
        )
        data = []
        for user_id in normalized_playtimes.keys():
            for game_id, value in normalized_playtimes[user_id].items():
                if len(normalized_playtimes[user_id].items()) >= p["min_game_count"]:
                    data.append(
                        {
                            "user_id": int(user_id),
                            "game_id": int(game_id),
                            "playtime": value,
                        }
                    )
        data = pd.DataFrame(data)
        data = data.sample(frac=1, replace=False)
        l = len(data)
        train = data[: round(l * 0.8) - 1].copy()
        val = data[round(l * 0.8) :].copy()
        train_user_ids = np.sort(np.unique(train.user_id.values))
        num_users = len(train_user_ids)
        userid2idx = {o: i for i, o in enumerate(train_user_ids)}
        train["user_id"] = train["user_id"].apply(lambda x: userid2idx[x])
        val["user_id"] = val["user_id"].apply(lambda x: userid2idx.get(x, -1))
        val = val[val["user_id"] >= 0].copy()
        train_game_ids = np.sort(np.unique(train.game_id.values))
        num_items = len(train_game_ids)
        gameid2idx = {o: i for i, o in enumerate(train_game_ids)}
        train["game_id"] = train["game_id"].apply(lambda x: gameid2idx[x])
        val["game_id"] = val["game_id"].apply(lambda x: gameid2idx.get(x, -1))
        val = val[val["game_id"] >= 0].copy()

        def valid_loss(model):
            model.eval()
            users = torch.LongTensor(val.user_id.values).cuda()
            items = torch.LongTensor(val.game_id.values).cuda()
            ratings = torch.FloatTensor(val.playtime.values).cuda()
            y_hat = model(users, items)
            loss = F.mse_loss(y_hat, ratings)
            return loss.item()

        def train_epocs(model, epochs=10, lr=0.01, wd=0.0):
            optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
            for i in range(epochs):
                model.train()
                users = torch.LongTensor(train.user_id.values).cuda()
                items = torch.LongTensor(train.game_id.values).cuda()
                ratings = torch.FloatTensor(train.playtime.values).cuda()
                y_hat = model(users, items)
                loss = F.mse_loss(y_hat, ratings)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                testloss = valid_loss(model)
            print(
                "train loss %.3f valid loss %.3f" % (loss.item(), testloss)
            )

        model = MF(num_users, num_items, emb_size=200).cuda()
        train_epocs(model, epochs=200, lr=1, wd=1e-5)
        train_epocs(model, epochs=200, lr=0.1, wd=1e-5)
        train_epocs(model, epochs=200, lr=0.01, wd=1e-5)
        train_epocs(model, epochs=200, lr=0.001, wd=1e-5)
        torch.save(model.state_dict(), user_data_dir / "model.dat")
        with (user_data_dir / "userid2idx.json").open("w") as data_file:
            json.dump({int(k): int(v) for k, v in userid2idx.items()}, data_file)
        with (user_data_dir / "gameid2idx.json").open("w") as data_file:
            json.dump({int(k): int(v) for k, v in gameid2idx.items()}, data_file)
        system.date_time = dt.datetime.now()
        system.save()


def update_mobcf_for_user(user, **current_parameters):
    p = ParametersManager(
        "mobcf_for_user",
        current_parameters,
        {"min_player_count": 20, "min_game_count": 10, "zscore": True},
    )
    if p.is_diff_last_current():
        q = User.update({User.mobcf_update_time:None}).where(User.mobcf_update_time != None).execute()
    if days_delta(User.get_by_id(user.id).mobcf_update_time) >= 1 or not user.mobcf:
        update_mobcf(
            min_player_count=p["min_player_count"],
            zscore=p["zscore"],
            min_game_count=p["min_game_count"],
        )
        with (user_data_dir / "userid2idx.json").open() as data_file:
            userid2idx = {int(k): v for k, v in json.load(data_file).items()}
        with (user_data_dir / "gameid2idx.json").open() as data_file:
            gameid2idx = {int(k): v for k, v in json.load(data_file).items()}
        num_users = len(userid2idx)
        num_items = len(gameid2idx)
        model = MF(num_users, num_items, emb_size=200).cuda()
        model.load_state_dict(torch.load(user_data_dir / "model.dat"))
        model.eval()
        if user.id in userid2idx:
            users = torch.LongTensor([userid2idx[user.id]]).cuda()
            games = list(gameid2idx.values())
            items = torch.LongTensor(games).cuda()
            result = model(users, items)
            idx2gameid = {value: key for key, value in gameid2idx.items()}
            result = {
                idx2gameid[game_idx.item()]: score.item()
                for score, game_idx in zip(result, items)
            }
            last_played = np.quantile(
                [
                    ug.last_played
                    for ug in UserGame.select(UserGame.last_played).where(
                        (UserGame.user == user) & (UserGame.playtime > 0)
                    )
                ],
                0.05,
            )
            played_games = [
                ug.game
                for ug in UserGame.select().where(
                    (UserGame.user == user)
                    & (UserGame.playtime > 0)
                    & (UserGame.last_played >= last_played)
                )
            ]
            games = {
                Game.get_by_id(key): value
                for key, value in sorted(
                    result.items(), key=lambda item: item[1], reverse=True
                )
            }
            user.mobcf = {
                game.id: score
                for game, score in games.items()
                if game not in played_games
                and game.player_count > p["min_player_count"]
                and game.rating >= 7
            }
            user.mobcf_update_time = dt.datetime.now()
            user.save()


def update_hr_for_user(user, **current_parameters):
    p = ParametersManager(
        "hr_for_user",
        current_parameters,
        {"cbr_coef": 0.5, "mbcf_coef": 0.5, "mobcf_coef": 0.5},
    )
    if p.is_diff_last_current():
        q = User.update({User.hr_update_time:None}).where(User.hr_update_time != None).execute()
    if days_delta(User.get_by_id(user.id).hr_update_time) >= 1 or not user.hr:
        print(f"update hr for {user.username}")
        update_cbr_for_user(user)
        update_mbcf_for_user(user)
        update_mobcf_for_user(user)
        user.hr = merge_dicts(
            [
                normalize_dict(user.cbr, p["cbr_coef"]) if user.cbr else [],
                normalize_dict(user.mbcf, p["mbcf_coef"]) if user.mbcf else [],
                normalize_dict(user.mobcf, p["mobcf_coef"]) if user.mobcf else [],
            ]
        )
        user.hr_update_time = dt.datetime.now()
        user.save()
