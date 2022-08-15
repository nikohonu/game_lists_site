import atexit
import os
from pathlib import Path

import appdirs
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from game_lists_site.blueprints.games import update_game_statistics

user_data_dir = Path(appdirs.user_data_dir(
    appauthor='Niko Honue', appname='game_lists_site'))
user_data_dir.mkdir(exist_ok=True, parents=True)
database_dir = user_data_dir / 'game_lists_site.db'


# Application Factory function
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=str(database_dir),
    )

    if test_config is None:
        # ./instance/config.py
        app.config.from_pyfile('config.py')
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    import game_lists_site.db as db
    db.init_app(app)

    import game_lists_site.blueprints.auth as auth
    import game_lists_site.models as models
    app.register_blueprint(auth.bp)

    import game_lists_site.blueprints.blog as blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')

    import game_lists_site.blueprints.user as user
    app.register_blueprint(user.bp)

    import game_lists_site.blueprints.steam as steam
    app.register_blueprint(steam.bp)

    import game_lists_site.blueprints.games as games
    app.register_blueprint(games.bp)

    # cron start
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_game_statistics, trigger='interval', hours=1)
    scheduler.start()
    # cron end

    return app
