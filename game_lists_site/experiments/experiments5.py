
import random

import numpy as np

from game_lists_site.models import System, User, UserGame
from game_lists_site.utils.utils import get_mbcf_for_user


def get_check_games(user: User):
    played_user_games = (
        UserGame.select().where(UserGame.user == user).where(UserGame.playtime > 0)
    )
    quantile = None
    if len(played_user_games) > 10:
        quantile = np.quantile([ug.last_played for ug in played_user_games], 0.90)
        return [ug.game for ug in played_user_games if ug.last_played > quantile]
    else:
        return []


def main():
    users = User.select()
    users = [
        User.get_by_id(user_id)
        for user_id in [
            76561198083927294,
            76561198091812571,
            76561198094109207,
            76561198394079733,
        ]
    ]
    # user = User.get_by_id(76561198091812571)
    best_avg_accuracy = 0.0
    best_max_player_count = 0
    best_normalize = True
    best_corrcoef = False
    best_sim_user_count = 9
    for i in range(5):
        accuracies = []
        max_player_count = random.randrange(10, 21)
        # max_player_count = 16
        normalize = True
        corrcoef = random.choice([True, False])
        # corrcoef = True
        sim_user_count = random.randrange(5, 15)
        # sim_user_count = 9
        print("-" * 10 + f"Stage {i}" + "-" * 10)
        print("max_player_count:" + str(max_player_count))
        print("normalize:" + str(normalize))
        print("corrcoef:" + str(corrcoef))
        print("sim_user_count:" + str(sim_user_count))
        for user in users:
            result = get_mbcf_for_user(
                user, 9, max_player_count, normalize, corrcoef, sim_user_count
            )
            check_game = get_check_games(user)
            if len(check_game) > 5 and result:
                accuracy = 0
                for game in check_game:
                    if game in result:
                        accuracy += 1
                accuracy = accuracy / len(check_game)
                accuracies.append(accuracy)
                # print("accuracy", accuracy, 'games', len(list(UserGame.select().where(UserGame.user==user).where(UserGame.playtime > 0))))
        system, _ = System.get_or_create(key="UserMBCF")
        system.date_time_value = None
        system.save()
        accuracy = np.average(accuracies)
        print("accuracy:" + str(accuracy))
        if accuracy >= best_avg_accuracy:
            best_max_player_count = max_player_count
            best_normalize = normalize
            best_corrcoef = corrcoef
            best_sim_user_count = sim_user_count
            best_avg_accuracy = accuracy
        print("Best")
        print("max_player_count:" + str(best_max_player_count))
        print("normalize:" + str(best_normalize))
        print("corrcoef:" + str(best_corrcoef))
        print("sim_user_count:" + str(best_sim_user_count))
        print("accuracy:" + str(best_avg_accuracy))


if __name__ == "__main__":
    main()
