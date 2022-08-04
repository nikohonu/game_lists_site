# Application Factory -> Instance of Flask application
import os
from pathlib import Path

import appdirs
from flask import Flask

user_data_dir = Path(appdirs.user_data_dir(
    appauthor='Niko Honue', appname='game_lists_site'))
user_data_dir.mkdir(exist_ok=True, parents=True)
database_dir = user_data_dir / 'game_lists_site.db'


# Application Factory function
def create_app(test_config=None):
    # Create and configure the app
    # creates the Flask instance
    app = Flask(__name__, instance_relative_config=True)
    # __name__ is the current Python module
    # instance_relative_config=True tells the app that configurations files are relative to the instance folder
    app.config.from_mapping(
        # Used by Flask and extensions to keep data safe
        SECRET_KEY='dev',
        # The path where SQLIte database file will be saved
        DATABASE=str(database_dir)
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        # app.config.from_pyfile() overrides the default configuration with values taken from the config.py
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        # os.makedirs() ensures that app.instance_path exists
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, world!'

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')

    return app
