import datetime as dt

from game_lists_site.models import Game, System
from game_lists_site.utils.utils import get_cbr_for_game


def main():
    game = Game.get_by_id(400)
    result = get_cbr_for_game(game)
    output_example = "{<Game: 620>: 0.8479002955787925, <Game: 220>: 0.6538461538461536, <Game: 70>: 0.6145098677990269, <Game: 233130>: 0.5559369874958259, <Game: 320>: 0.5370861555295746, <Game: 278360>: 0.5200314339611525, <Game: 362890>: 0.5120915564991891, <Game: 223470>: 0.5098499285104607, <Game: 418370>: 0.5098499285104607}"
    print(result)
    print("-" * 32)
    print(output_example)
    system, _ = System.get_or_create(key="GameCBR")
    system.date_time_value = None
    system.save()


if __name__ == "__main__":
    main()
