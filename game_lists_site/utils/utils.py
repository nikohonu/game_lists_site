import datetime as dt
import json
from operator import itemgetter

import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn import preprocessing
import torch
import torch.nn as nn
import torch.nn.functional as F
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
    UserSimilarity,
    user_data_dir,
)


def days_delta(datetime):
    if not datetime:
        return float("inf")
    return (dt.datetime.now() - datetime).days


def get_game(game_id: int):
    game = Game.get_or_none(Game.id == game_id)
    if not game or not game.last_update_time or days_delta(game.last_update_time) >= 7:
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
        genre_blacklist = []
        genre_blacklist.extend(range(50, 60 + 1))
        genre_blacklist.extend(range(80, 85 + 1))
        for genre_dict in data.get("genres", []):
            genre, _ = Genre.get_or_create(
                id=genre_dict["id"], name=genre_dict["description"]
            )
            if genre.id in genre_blacklist:
                continue
            if genre.id == 37:
                game.free_to_play = True
            GameGenre.get_or_create(game=game, genre=genre)
        for tag_name in steam.get_app_tags(game.id):
            tag, _ = Tag.get_or_create(name=tag_name)
            GameTag.get_or_create(game=game, tag=tag)
        game.rating = steam.get_app_rating(game.id)
        game.last_update_time = dt.datetime.now()
        game.save()
    return game


def get_game_stats(game: Game):
    game_stats = GameStats.get_or_none(GameStats.game == game)
    if not game_stats or days_delta(game_stats.last_update_time) >= 7:
        game_stats, _ = GameStats.get_or_create(game=game)
        # features
        features = []
        features += [
            game_developer.developer.name.replace(" ", "")
            for game_developer in GameDeveloper.select(GameDeveloper.developer).where(
                GameDeveloper.game == game
            )
        ]
        features += [
            game_genre.genre.name.replace(" ", "")
            for game_genre in GameGenre.select(GameGenre.genre).where(
                GameGenre.game == game
            )
        ]
        features += [
            game_tag.tag.name.replace(" ", "")
            for game_tag in GameTag.select(GameTag.tag).where(GameTag.game == game)
        ]
        game_stats.features = " ".join(features)
        # features end
        users_game = UserGame.select(UserGame.playtime, UserGame.score).where(
            UserGame.game == game
        )
        users_game_with_playtime = users_game.where(UserGame.playtime > 0)
        users_game_with_score = users_game.where(UserGame.score > 0)
        game_stats.player_count = users_game_with_playtime.count()
        playtimes = np.array([ug.playtime for ug in users_game_with_playtime])
        scores = np.array([ug.score for ug in users_game_with_score])
        if len(playtimes) > 0:
            game_stats.total_playtime = np.sum(playtimes)
            game_stats.mean_playtime = np.mean(playtimes)
            game_stats.median_playtime = np.median(playtimes)
            game_stats.max_playtime = np.max(playtimes)
            game_stats.min_playtime = np.min(playtimes)
            if len(scores) > 2:
                game_stats.rating = np.mean(scores)
            else:
                game_stats.rating = 0
        game_stats.last_update_time = dt.datetime.now()
        game_stats.save()
    return game_stats


def get_cbr_for_game(game, result_count=9, min_player_count=28):
    system, _ = System.get_or_create(key="GameCBR")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        GameCBR.delete().execute()
        games = []
        features = []
        for gs in GameStats.select(GameStats.game, GameStats.features).where(
            GameStats.player_count >= min_player_count
        ):
            games.append(gs.game)
            features.append(gs.features)
        vectorizer = CountVectorizer()
        X = vectorizer.fit_transform(features)
        csr = cosine_similarity(X, X)  # cosine similarity result
        for g_a, row in zip(games, csr):
            l = 0
            precision = 0.7
            while l < max(28, result_count):  # this
                result = dict(
                    sorted(
                        [
                            (g_b.id, value)
                            for g_b, value in zip(games, row)
                            if value >= precision
                        ],
                        key=itemgetter(1),
                        reverse=True,
                    )
                )
                l = len(result)
                precision -= 0.05
            game_cbr, _ = GameCBR.get_or_create(game=g_a)
            game_cbr.data = json.dumps(result)
            game_cbr.save()
        system.date_time_value = dt.datetime.now()
        system.save()
    game_cbr = GameCBR.get_or_none(game=game)
    if game_cbr:
        data = {
            Game.get_by_id(game_id): value
            for game_id, value in json.loads(game_cbr.data).items()
        }
        return dict(list(data.items())[1 : result_count + 1])
    else:
        return {}


def get_cbr_for_user(
    user, result_count=-1, min_player_count=24, cbr_for_game_result_count=2
):
    if not user.last_cbr_update_time or days_delta(user.last_cbr_update_time) >= 7:
        played_user_games = UserGame.select(
            UserGame.game, UserGame.last_played, UserGame.score
        ).where((UserGame.user == user) & (UserGame.playtime > 0))
        last_played = np.quantile([ug.last_played for ug in played_user_games], 0.1)
        played_user_games = played_user_games.where(UserGame.last_played >= last_played)
        played_games = [ug.game for ug in played_user_games]
        user_games_with_score = played_user_games.where(UserGame.score > 0)
        games_with_score = [ug.game for ug in user_games_with_score]
        result = {}
        for user_game, game_cbr_result in zip(
            user_games_with_score,
            [
                get_cbr_for_game(g, cbr_for_game_result_count, min_player_count)
                for g in games_with_score
            ],
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
        user_cbr.data = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        user_cbr.save()
        user.last_benchmark_cbr_update_time = dt.datetime.now()
        user.save()
    data = UserCBR.get_or_none(UserCBR.user == user).data
    if data:
        if result_count != -1:
            return dict(list(data.items())[:result_count])
        else:
            return dict(list(data.items()))
    else:
        {}


def get_normalized_playtimes(min_player_count, normalize, zscore_norm):
    games = [
        gs.game
        for gs in GameStats.select(GameStats.game).where(
            GameStats.player_count >= min_player_count
        )
    ]
    users_games = UserGame.select(UserGame.playtime, UserGame.user).where(
        UserGame.playtime > 0
    )
    result = {}
    for game in games:
        users_game = users_games.where(UserGame.game == game)
        playtimes = [user_game.playtime for user_game in users_game]
        if normalize:
            if zscore_norm:
                playtimes = stats.zscore(playtimes)
            else:
                playtimes = preprocessing.normalize([playtimes])[0]
        result[game.id] = {
            ug.user.id: playtime for ug, playtime in zip(users_game, playtimes)
        }
    return result


def get_similar_users(
    user,
    normalized_playtimes,
    max_count=-1,
    corrcoef=False,
):
    system, _ = System.get_or_create(key="UserSimilarity")
    if not system.date_time_value or days_delta(system.date_time_value) >= 7:
        games = list(normalized_playtimes.keys())
        users = {}
        for game in normalized_playtimes.keys():
            for u in normalized_playtimes[game].keys():
                if u in users:
                    users[u] += 1
                else:
                    users[u] = 1
        users = [u for u, game_count in users.items() if game_count >= 10]
        game_vecs = []
        for game in games:
            game_vec = []
            for u in users:
                value = normalized_playtimes[game].get(u)
                game_vec.append(value if value else 0)
            game_vecs.append(game_vec)
        game_vecs = np.array(game_vecs, dtype=np.float32)
        user_vecs = np.flip(np.rot90(game_vecs), 0)
        if corrcoef:
            user_vecs = np.corrcoef(user_vecs)
        else:
            user_vecs = cosine_similarity(user_vecs)
        users_sim = {}
        UserSimilarity.delete().execute()
        for u_a, user_vec in zip(users, user_vecs):
            result = []
            for u_b, value in zip(users, user_vec):
                result.append((u_b, float(value)))
            UserSimilarity.create(
                user=User.get_by_id(u_a),
                data=dict(sorted(result, key=lambda x: x[1], reverse=True)),
            )
        system.date_time_value = dt.datetime.now()
        system.save()
    user_similarity = UserSimilarity.get_or_none(UserSimilarity.user == user)
    if user_similarity:
        if max_count == -1:
            return user_similarity.data
        else:
            return dict(list(user_similarity.data.items())[1 : max_count + 1])
    else:
        return {}


def get_mbcf_for_user(
    user,
    max_count=-1,
    min_player_count=39,
    sim_user_count=36,
    zscore_norm=False,
    corrcoef=True,
):
    if not user.last_mbcf_update_time or days_delta(user.last_mbcf_update_time) >= 7:
        normalized_playtimes = get_normalized_playtimes(
            min_player_count, True, zscore_norm
        )
        users_sim = get_similar_users(
            user, normalized_playtimes, sim_user_count, corrcoef
        )
        played_user_games = UserGame.select(
            UserGame.game, UserGame.last_played, UserGame.score
        ).where((UserGame.user == user) & (UserGame.playtime > 0))
        last_played = np.quantile([ug.last_played for ug in played_user_games], 0.8)
        played_user_games = played_user_games.where(UserGame.last_played < last_played)
        played_games = [ug.game for ug in played_user_games]
        played_game_ids = [g.id for g in played_games]
        result = {}
        for game_id in normalized_playtimes.keys():
            if game_id not in played_game_ids:
                for user_id, value in users_sim.items():
                    pt = normalized_playtimes[game_id].get(int(user_id))
                    if pt:
                        if game_id in result:
                            result[game_id] += pt * value
                        else:
                            result[game_id] = pt * value
        user_mbcf, _ = UserMBCF.get_or_create(
            user=user,
        )
        user_mbcf.data = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        user_mbcf.save()
        user.last_mbcf_update_time = dt.datetime.now()
        user.save()
    user_mbcf = UserMBCF.get_or_none(UserMBCF.user == user)
    if user_mbcf:
        data = {
            Game.get_by_id(int(key)): value for key, value in user_mbcf.data.items()
        }
        if max_count == -1:
            return data
        else:
            return dict(list(data.items())[:max_count])
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

        model = MF(num_users, num_items, emb_size=200).cuda()
        train_epocs(model, epochs=200, lr=1, wd=1e-5)
        train_epocs(model, epochs=200, lr=0.1, wd=1e-5)
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
    model = MF(num_users, num_items, emb_size=200).cuda()
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
    return {k: v for k, v in zip(dict_data, values)}


def get_hrs_for_user(
    target_user, max_count=-1, cbr_coef=0.27, mbcf_coef=0.95, mobcf_coef=0.62
):
    cbr_result = get_cbr_for_user(target_user)
    mbcf_result = get_mbcf_for_user(target_user)
    mobcf_result = get_mobcf_for_user(target_user)
    result = merge_dicts(
        [
            normalize_dict(cbr_result, cbr_coef),
            normalize_dict(mbcf_result, mbcf_coef),
            normalize_dict(mobcf_result, mobcf_coef),
        ]
    )
    if max_count == -1:
        return result
    else:
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

