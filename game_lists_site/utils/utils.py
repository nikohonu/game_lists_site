import datetime as dt
import json
from operator import itemgetter

import numpy as np
import pandas as pd
import scipy.stats as stats
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn import preprocessing
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import game_lists_site.utils.steam as steam
from game_lists_site.models import (
    Developer,
    Game,
    GameCBR,
    GameDeveloper,
    GameGenre,
    GameMBCF,
    GameStats,
    GameTag,
    Genre,
    System,
    Tag,
    User,
    UserCBR,
    UserGame,
    UserMBCF,
    user_data_dir,
)


def days_delta(datetime):
    if not datetime:
        return float("inf")
    current_date = dt.datetime.now()
    return (current_date - datetime).days


def get_game(game_id: int):
    game = Game.get_or_none(Game.id == game_id)
    if not game or not game.last_update_time or days_delta(game.last_update_time) >= 7:
        if game:
            print(game.last_update_time)
        data = steam.get_app_details(game_id)
        if not data:
            return None
        if not game:
            game, _ = Game.get_or_create(id=data["steam_appid"], name=data["name"])
        game.description = data.get("about_the_game", "")
        if data["release_date"]["date"]:
            try:
                game.release_date = dt.datetime.strptime(
                    data["release_date"]["date"], "%d %b, %Y"
                ).date()
            except:
                game.release_date = None
        game.image_url = data["header_image"]
        # clear
        q = GameDeveloper.delete().where(GameDeveloper.game == game)
        q.execute()
        q = GameGenre.delete().where(GameGenre.game == game)
        q.execute()
        q = GameTag.delete().where(GameTag.game == game)
        q.execute()
        # clear end
        for developer_name in data.get("developers", []):
            developer, _ = Developer.get_or_create(name=developer_name)
            GameDeveloper.get_or_create(game=game, developer=developer)
        for genre_dict in data.get("genres", []):
            genre, _ = Genre.get_or_create(
                id=genre_dict["id"], name=genre_dict["description"]
            )
            GameGenre.get_or_create(game=game, genre=genre)
        for tag_name in steam.get_app_tags(game.id):
            tag, _ = Tag.get_or_create(name=tag_name)
            GameTag.get_or_create(game=game, tag=tag)
        game.rating = steam.get_app_rating(game.id)
        game.last_update_time = dt.datetime.now()
        game.save()
    return game


game_stats_data = {gs.game: gs for gs in GameStats.select()}


def get_game_stats(game: Game):
    if game in game_stats_data:
        game_stats = game_stats_data[game]
    else:
        game_stats = None
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        # features
        features = []
        features += [
            game_developer.developer.name.replace(" ", "")
            for game_developer in GameDeveloper.select().where(
                GameDeveloper.game == game
            )
        ]
        features += [
            game_genre.genre.name.replace(" ", "")
            for game_genre in GameGenre.select().where(GameGenre.game == game)
        ]
        features += [
            game_tag.tag.name.replace(" ", "")
            for game_tag in GameTag.select().where(GameTag.game == game)
        ]
        # features end
        game_stats.player_count = len(
            UserGame.select().where(UserGame.game == game).where(UserGame.playtime > 0)
        )
        game_stats.features = " ".join(features)
        if game.rating == None:
            game.rating = steam.get_app_rating(game.id)
            game.save()
        playtimes = np.array([ug.playtime for ug in UserGame.select().where(UserGame.game == game).where(UserGame.playtime > 0)])
        if len(playtimes) > 0:
            game_stats.total_playtime = np.sum(playtimes)
            game_stats.mean_playtime = np.mean(playtimes)
            game_stats.median_playtime = np.median(playtimes)
            game_stats.max_playtime = np.max(playtimes)
            game_stats.min_playtime = np.min(playtimes)
            
        game_stats.last_update_time = dt.datetime.now()
        game_stats.save()
    return game_stats


def get_cbr_for_game(target_game, result_count=9):
    system, _ = System.get_or_create(key="GameCBR")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        corpus = {}
        games = [
            game for game in Game.select() if get_game_stats(game).player_count > 5
        ]  # min_player_count = 16 is better, because the tests say so
        for game in games:
            corpus[game] = get_game_stats(game).features
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform(corpus.values())
        cosine_similarity_result = cosine_similarity(X, X)
        for game_a, row in zip(games, cosine_similarity_result):
            result = [
                (game_b.id, value) for game_b, value in zip(games, row) if value >= 0.5
            ]
            result = dict(sorted(result, key=itemgetter(1), reverse=True))
            game_cbr, _ = GameCBR.get_or_create(game=game_a)
            game_cbr.data = json.dumps(result)
            game_cbr.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    game_cbr = GameCBR.get_or_none(game=target_game)
    if game_cbr:
        data = {
            Game.get_by_id(game_id): value
            for game_id, value in json.loads(game_cbr.data).items()
        }
        if len(data) > result_count + 1:
            return dict(list(data.items())[1 : result_count + 1])
        else:
            return dict(list(data.items())[1:])
    else:
        return {}


def get_cbr_for_user(user, result_count=9):
    if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
        print("get_cbr_for_user")
        played_user_games = (
            UserGame.select().where(UserGame.user == user).where(UserGame.playtime > 0)
        )
        played_games = [ug.game for ug in played_user_games]
        user_games_with_score = played_user_games.where(UserGame.score != None)
        games_with_score = [ug.game for ug in user_games_with_score]
        result = {}
        # best_game_cbr_result_count = 6 is better, because the tests say so
        for user_game, game_cbr_result in zip(
            user_games_with_score, [get_cbr_for_game(g, 6) for g in games_with_score]
        ):
            if game_cbr_result:
                for sim_game in game_cbr_result:
                    if sim_game not in played_games and sim_game.rating >= 7:
                        if sim_game.id not in result:
                            result[sim_game.id] = (
                                user_game.score * game_cbr_result[sim_game]
                            )
                        else:
                            result[sim_game.id] += (
                                user_game.score * game_cbr_result[sim_game]
                            )
        user_cbr, _ = UserCBR.get_or_create(user=user)
        user_cbr.data = json.dumps(
            dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        )
        user_cbr.save()
        user.last_cbr_update_time = dt.datetime.now()
        user.save()
    data = {
        Game.get_by_id(game_id): value
        for game_id, value in json.loads(
            UserCBR.get_or_none(UserCBR.user == user).data
        ).items()
    }
    if len(data) > result_count:
        return dict(list(data.items())[:result_count])
    else:
        return data


def get_normalized_playtimes(min_player_count=5, normalize=True, zscore_norm=False):
    system, _ = System.get_or_create(key="NormalizedPlaytime")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        games = [
            game
            for game in Game.select()
            if get_game_stats(game).player_count >= min_player_count
        ]
        result = {}
        for game in games:
            user_games = (
                UserGame.select()
                .where(UserGame.game == game)
                .where(UserGame.playtime > 0)
            )
            playtimes = [user_game.playtime for user_game in user_games]
            normalized_playtimes = []
            if normalize:
                if zscore_norm:
                    normalized_playtimes = stats.zscore(playtimes)
                else:
                    normalized_playtimes = preprocessing.normalize([playtimes])[0]
            else:
                normalized_playtimes = playtimes
            result[game.id] = {
                ug.user.id: normalized_playtime
                for ug, normalized_playtime in zip(user_games, normalized_playtimes)
            }
        with (user_data_dir / "normalized_playtimes.json").open("w") as data_file:
            json.dump(result, data_file)
        system.date_time_value = dt.datetime.now()
        system.save()
        return result
    else:
        with (user_data_dir / "normalized_playtimes.json").open() as data_file:
            result = {
                int(key_a): {int(key_b): value_b for key_b, value_b in value_a.items()}
                for key_a, value_a in json.load(data_file).items()
            }
        return result


def get_mbcf_for_user(
    target_user,
    max_count=-1,
    max_player_count=16,
    normalize=True,
    corrcoef=True,
    sim_user_count=9,
):
    system, _ = System.get_or_create(key="UserMBCF")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        normalized_playtimes = get_normalized_playtimes(max_player_count, normalize)
        games = Game.select()
        users = [
            user
            for user in User.select()
            if len(
                UserGame.select()
                .where(UserGame.user == user)
                .where(UserGame.playtime != None)
            )
            >= 10
        ]
        game_vecs = []
        for game in games:
            if not normalized_playtimes.get(game.id):
                continue
            game_vec = {user: 0 for user in users}
            user_games = [
                ug
                for ug in UserGame.select().where(UserGame.game == game)
                if normalized_playtimes[game.id].get(ug.user.id)
            ]
            for ug in user_games:
                if ug.user in game_vec:
                    game_vec[ug.user] = normalized_playtimes[game.id].get(ug.user.id)
            game_vecs.append(list(game_vec.values()))
        game_vecs = np.array(game_vecs, dtype=np.float32)
        user_vecs = np.flip(np.rot90(game_vecs), 0)
        if corrcoef:
            user_vecs = np.corrcoef(user_vecs)
        else:
            user_vecs = cosine_similarity(user_vecs)
        sim_users = {}
        for user, user_vec in zip(users, user_vecs):
            result = {}
            for u, sim in zip(users, user_vec):
                result[u] = float(sim)
            result = dict(
                sorted(result.items(), key=lambda x: x[1], reverse=True)[
                    1 : sim_user_count + 1
                ]
            )
            sim_users[user] = result
        i = 0
        count = len(sim_users)
        for user_a, sim in sim_users.items():
            print(f"{i/count*100:.2f}%", end="")
            print("\r", end="")
            i += 1
            played_games = set()
            played_user_games = (
                UserGame.select()
                .where(UserGame.user == user_a)
                .where(UserGame.playtime > 0)
            )
            if len(played_user_games) > 1:
                quantile = np.quantile(
                    [ug.last_played for ug in played_user_games], 0.10
                )
                check_user_games = [
                    ug for ug in played_user_games if ug.last_played <= quantile
                ]
                for ug in played_user_games:
                    if ug not in check_user_games:
                        played_games.add(ug.game)
                played_games = list(played_games)
            games = {}
            for user_b, value in sim.items():
                for user_game in (
                    UserGame.select()
                    .where(UserGame.user == user_b)
                    .where(UserGame.playtime != None)
                ):
                    game = user_game.game
                    user = user_game.user
                    if (
                        game not in played_games
                        and game.id in normalized_playtimes
                        and user.id in normalized_playtimes[game.id]
                        and game.rating >= 7
                    ):
                        if game.id in games:
                            games[game.id] += (
                                normalized_playtimes[game.id].get(user.id) * value
                            )
                        else:
                            games[game.id] = (
                                normalized_playtimes[game.id].get(user.id) * value
                            )
            games = dict(sorted(games.items(), key=lambda x: x[1], reverse=True))
            user_mbcf, _ = UserMBCF.get_or_create(user=user_a)
            user_mbcf.data = json.dumps(games)
            user_mbcf.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    user_mbcf = UserMBCF.get_or_none(UserMBCF.user == target_user)
    if user_mbcf:
        data = {
            Game.get_by_id(game_id): value
            for game_id, value in json.loads(user_mbcf.data).items()
        }
        if len(data) > max_count:
            return dict(list(data.items())[:max_count])
        else:
            return data
    else:
        return {}


def get_mbcf_for_game(
    target_game,
    max_count=-1,
    max_player_count=16,
):
    system, _ = System.get_or_create(key="GameMBCF")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        normalized_playtimes = get_normalized_playtimes(5, False)
        games = [
            game for game in Game.select() if get_game_stats(game).player_count >= 5
        ]
        users = User.select()
        game_vecs = []
        for game in games:
            if not normalized_playtimes.get(game.id):
                continue
            game_vec = {user: 0 for user in users}
            user_games = [
                ug
                for ug in UserGame.select().where(UserGame.game == game)
                if normalized_playtimes[game.id].get(ug.user.id)
            ]
            for ug in user_games:
                if ug.user in game_vec:
                    game_vec[ug.user] = normalized_playtimes[game.id].get(ug.user.id)
            game_vecs.append(list(game_vec.values()))
        game_vecs = np.array(game_vecs, dtype=np.float32)
        game_vecs = np.corrcoef(game_vecs)
        for game, game_vec in zip(games, game_vecs):
            result = {}
            for g, sim in zip(games, game_vec):
                result[g.id] = sim
            result = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
            game_mbcf, _ = GameMBCF.get_or_create(game=game)
            game_mbcf.data = json.dumps(result)
            game_mbcf.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    game_mbcf = GameMBCF.get_or_none(GameMBCF.game == target_game)
    if game_mbcf:
        data = {
            Game.get_by_id(game_id): value
            for game_id, value in json.loads(game_mbcf.data).items()
        }
        if len(data) > max_count + 1:
            return dict(list(data.items())[1 : max_count + 1])
        else:
            return data
    else:
        return {}


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
        result = {
            idx2gameid[game_idx.item()]: score.item()
            for score, game_idx in zip(result, items)
        }
        played_games = [
            ug.game
            for ug in UserGame.select()
            .where(UserGame.user == target_user)
            .where(UserGame.playtime > 0)
        ]
        games = {
            Game.get_by_id(key): value
            for key, value in sorted(
                result.items(), key=lambda item: item[1], reverse=True
            )
        }
        data = [
            (game, score)
            for game, score in games.items()
            if game not in played_games
            and get_game_stats(game).player_count > 10
            and game.rating >= 7
        ]
        if len(data) > max_count:
            return dict(data[:max_count])
        else:
            return dict(data)
    else:
        return {}


def merge_dicts(dicts: list):
    result = {}
    for d in dicts:
        for v in d:
            if v in result:
                result[v] += d[v]
            else:
                result[v] = d[v]
    result = {
        key: value
        for key, value in sorted(result.items(), key=lambda item: item[1], reverse=True)
    }
    return result


def normalize_dict(dict_data: dict, coef: float = 1):
    values = list(dict_data.values())
    values = preprocessing.normalize([values])[0] * coef
    print(type(values))
    return {k: v for k, v in zip(dict_data, values)}


def get_hrs_for_user(target_user, max_count=9):
    cbr_result = get_cbr_for_user(target_user, 36)
    mbcf_result = get_mbcf_for_user(target_user, 36)
    mobcf_result = get_mobcf_for_user(target_user, 36)
    result = merge_dicts(
        [
            normalize_dict(cbr_result, 0.5),
            normalize_dict(mbcf_result, 0.5),
            normalize_dict(mobcf_result, 0.5),
        ]
    )
    return {k: v for k, v in list(result.items())[:max_count]}

def get_hrs_for_game(target_game, max_count=9):
    cbr_result = get_cbr_for_game(target_game, 36)
    mbcf_result = get_mbcf_for_game(target_game, 36)
    result = merge_dicts(
        [
            normalize_dict(cbr_result, 0.5),
            normalize_dict(mbcf_result, 0.25),
        ]
    )
    return {k: v for k, v in list(result.items())[:max_count]}

