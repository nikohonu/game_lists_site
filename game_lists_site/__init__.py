import os
from pathlib import Path

import appdirs
from flask import Flask

user_data_dir = Path(
    appdirs.user_data_dir(appauthor="Niko Honue", appname="game_lists_site")
)
user_data_dir.mkdir(exist_ok=True, parents=True)
database_dir = user_data_dir / "game_lists_site.db"


# Application Factory function
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(database_dir),
    )

    @app.context_processor
    def utility_processor():
        def prettify_playtime(minutes: int):
            minutes = round(minutes)
            int_hours = int(minutes / 60.0)
            round_hours = round(minutes / 60.0)
            if minutes < 60:
                return f"{minutes}m"
            elif int_hours <= 5:
                return f"{int_hours}h {minutes - int_hours * 60}m"
            else:
                return f"{round_hours}h"

        def prettify_playtime_with_days(minutes: int):
            minutes = int(minutes)
            hours = int(minutes / 60.0)
            days = int(hours / 24.0)
            years = int(days / 365.25)
            if minutes < 60:
                return f"{minutes}m"
            elif hours <= 5:
                return f"{hours}h {minutes - hours * 60}m"
            elif hours <= 1000:
                return f"{hours}h"
            elif days <= 365:
                return f"{days}d"
            else:
                return f"{years}y"

            # elif days <= 365:
                # return f"{days}d"
            # else:
            #     return f"{years}y"

        return dict(
            prettify_playtime=prettify_playtime,
            prettify_playtime_with_days=prettify_playtime_with_days,
        )

    if test_config is None:
        # ./instance/config.py
        app.config.from_pyfile("config.py")
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    import game_lists_site.blueprints.auth as auth
    import game_lists_site.models as models

    app.register_blueprint(auth.bp)

    import game_lists_site.blueprints.user as user

    app.register_blueprint(user.bp)

    import game_lists_site.blueprints.user_stats as user_stats

    app.register_blueprint(user_stats.bp)

    import game_lists_site.blueprints.steam as steam

    app.register_blueprint(steam.bp)

    import game_lists_site.blueprints.games as games

    app.register_blueprint(games.bp)

    import game_lists_site.blueprints.game as game

    app.register_blueprint(game.bp)

    import game_lists_site.blueprints.index as index

    app.register_blueprint(index.bp)
    app.add_url_rule("/", endpoint="index")

    return app
