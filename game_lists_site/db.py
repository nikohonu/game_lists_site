import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:  # g is a special object that is unique for each request
        # sqlite3.connect() establishes a connection to the file pointed at by DATABASE configuration key
        g.db = sqlite3.connect(
            # current_app is also a special object that points to the application handling the request
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # tells the to return rows that behave like dicts

    return g.db


def close_db(e=None):  # close_db() checks if a connection was created by checking if g.db was set
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    # open_resources() opens a file relative to Flaskr package, which is useful since you won`t know where the location is when deploying the application
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


# click.command() define a command called 'init-db' that calls init_db() function and shows a success message to the user
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables"""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    # tells Flask to cal that function when cleaning up after returning the response
    app.teardown_appcontext(close_db)
    # adds a new command that can be called with the flask command
    app.cli.add_command(init_db_command)
