import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import game_lists_site.utils.steam as steam
from game_lists_site.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        steam_profile_url = request.form['steam_profile_url']
        steam_profile_id = steam.get_profile_id_from_url(
            steam_profile_url) if steam_profile_url else None
        db = get_db()
        error = None
        if not username:
            error = 'Username is required!'
        elif not password:
            error = 'Password is required!'
        elif not steam_profile_url:
            error = 'Steam profile url is required!'
        elif not steam_profile_id:
            error = 'Invalid steam profile url!'
        if error is None:
            try:
                db.execute('INSERT INTO steam_profile (id) VALUES (?)',
                           (steam_profile_id,))
                db.commit()
                db.execute(
                    'INSERT INTO user (username, password, steam_profile_id) '
                    'VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), steam_profile_id),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()  # fetchone() returns one row from the query

        if user is None:
            error = 'Incorrect username.'
        # check_password_hash() hashes the submitted password in the same way as the stored and compares them
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()  # session is a dict that stores data across requests
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


# registers a function that runs before the view function, no matter what URL is requested
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# This function checks if a user is loaded and redirects to the login page otherwise
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            # url_for() function generates teh URL to a view based on a name and arguments
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
