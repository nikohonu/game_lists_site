import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from game_lists_site.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))  # @bp.route associates the URL '/register' with register view function
def register():
    if request.method == 'POST':
        username = request.form['username']  # request.form is a special type of dict mapping submitted form keys and values
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required!'
        elif not password:
            error = 'Password is required!'

        if error is None:
            try:
                db.execute(
                    'INSERT INTO user (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password)),
                )  # db.executes takes a SQL query with ? for any user input and a tuple of values to replace the placeholders with.
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
        elif not check_password_hash(user['password'], password):  # check_password_hash() hashes the submitted password in the same way as the stored and compares them
            error = 'Incorrect password.'

        if error is None:
            session.clear()  # session is a dict that stores data across requests
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request  # registers a function that runs before the view function, no matter what URL is requested
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


def login_required(view):  # This function checks if a user is loaded and redirects to the login page otherwise
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))  # url_for() function generates teh URL to a view based on a name and arguments

        return view(**kwargs)

    return wrapped_view
