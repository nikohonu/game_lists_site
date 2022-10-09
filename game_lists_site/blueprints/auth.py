import functools

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import game_lists_site.utils.steam as steam
from game_lists_site.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        steam_profile_url = request.form["steam_profile_url"]
        steam_id = (
            steam.get_steam_id_from_url(steam_profile_url)
            if steam_profile_url
            else None
        )
        error = None
        if not username:
            error = "Username is required!"
        elif not password:
            error = "Password is required!"
        elif not steam_profile_url:
            error = "Steam profile url is required!"
        elif not steam_id:
            error = "Invalid steam profile url!"
        if error is None:
            User.create(
                id=steam_id,
                username=username,
                password=generate_password_hash(password),
            )
            return redirect(url_for("auth.login"))
        flash(error)
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        user = User.get_or_none(username=username)
        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."
        if error is None:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("user.user", username=user.username))
        flash(error)
    return render_template("auth/login.html")


@bp.route("/delete", methods=["POST"])
def delete():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        user = User.get_or_none(username=username)
        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."
        if error is None:
            user.delete()
            return jsonify(True)
        flash(error)
    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = User.get_or_none(id=user_id)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
