from game_lists_site.models import User
from game_lists_site.utils.utils import get_cbr_for_user


def main():
    user = User.get_by_id(76561198091812571)
    result = get_cbr_for_user(user)
    output_example = "{<Game: 356190>: 23.605852482975283, <Game: 648800>: 18.236838249430612, <Game: 1930>: 17.014029362816007, <Game: 814380>: 16.29226600658098, <Game: 244850>: 15.1824273121713, <Game: 1281930>: 14.91723424029512, <Game: 582010>: 14.042318294164733, <Game: 1217060>: 13.588245551252175, <Game: 252490>: 12.932455402396467}"
    print(result)
    print("-" * 32)
    print(output_example)
    user.last_cbr_update_time = None
    user.save()


if __name__ == "__main__":
    main()
