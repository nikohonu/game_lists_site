import datetime as dt
import json

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

from game_lists_site.models import Game, System, User, UserGame, user_data_dir
from game_lists_site.utils.utils import (
    days_delta,
    get_game_stats,
    get_normalized_playtimes,
)


class MF(nn.Module):
    def __init__(self, num_users, num_items, emb_size=100):
        super(MF, self).__init__()
        self.user_emb = nn.Embedding(num_users, emb_size)
        self.item_emb = nn.Embedding(num_items, emb_size)

    def forward(self, u, v):
        u = self.user_emb(u)
        v = self.item_emb(v)
        return (u * v).sum(1)

    def print(self, u, v):
        u = self.user_emb(u)
        v = self.item_emb(v)
        print("u", u)
        print("v", u)


def get_mobcf_for_user(target_user: User, max_count=9):
    system, _ = System.get_or_create(key="UserMOBCF")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        normalized_playtimes = get_normalized_playtimes()
        data = pd.DataFrame(
            [
                {
                    "user_id": ug.user.id,
                    "game_id": ug.game.id,
                    "playtime": normalized_playtimes[ug.game.id][ug.user.id],
                    "last_played": ug.last_played,
                }
                for ug in UserGame.select()
                .join(User)
                .order_by(User.id)
                .where(UserGame.playtime > 0)
                if ug.game.id in normalized_playtimes
                and ug.user.id in normalized_playtimes[ug.game.id]
            ]
        )
        time_80 = np.quantile(data.last_played.values, 0.8)
        train = data[data["last_played"] < time_80].copy()
        val = data[data["last_played"] >= time_80].copy()
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
                print("train loss %.3f valid loss %.3f" % (loss.item(), testloss))

        model = MF(num_users, num_items, emb_size=1000).cuda()
        train_epocs(model, epochs=600, lr=1, wd=1e-5)
        train_epocs(model, epochs=600, lr=0.1, wd=1e-5)
        train_epocs(model, epochs=600, lr=0.01, wd=1e-5)
        train_epocs(model, epochs=600, lr=0.001, wd=1e-5)
        torch.save(model.state_dict(), user_data_dir / "model.dat")
        with (user_data_dir / "userid2idx.json").open("w") as data_file:
            json.dump({int(k): int(v) for k, v in userid2idx.items()}, data_file)
        with (user_data_dir / "gameid2idx.json").open("w") as data_file:
            json.dump({int(k): int(v) for k, v in gameid2idx.items()}, data_file)
        system.date_time_value = dt.datetime.now()
        system.save()
    with (user_data_dir / "userid2idx.json").open() as data_file:
        userid2idx = {int(k): v for k, v in json.load(data_file).items()}
    with (user_data_dir / "gameid2idx.json").open() as data_file:
        gameid2idx = {int(k): v for k, v in json.load(data_file).items()}
    num_users = len(userid2idx)
    num_items = len(gameid2idx)
    model = MF(num_users, num_items, emb_size=1000).cuda()
    model.load_state_dict(torch.load(user_data_dir / "model.dat"))
    model.eval()
    if target_user.id in userid2idx:
        users = torch.LongTensor([userid2idx[target_user.id]]).cuda()
        games = list(gameid2idx.values())
        items = torch.LongTensor(games).cuda()
        result = model(users, items)
        idx2gameid = {value: key for key, value in gameid2idx.items()}
        result = {idx2gameid[game_idx.item()]: score.item() for score, game_idx in zip(result, items)}
        played_games = [ug.game for ug in UserGame.select().where(UserGame.user == target_user).where(UserGame.playtime > 0)]
        games = {Game.get_by_id(key): value for key, value in sorted(result.items(), key=lambda item: item[1], reverse=True) }
        data = [(game, score) for game, score in games.items() if game not in played_games and get_game_stats(game).player_count > 10]
        if len(data) > max_count:
            return dict(data[:max_count])
        else:
            return dict(data)
    else:
        return {}
