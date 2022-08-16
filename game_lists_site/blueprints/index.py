from flask import Blueprint, abort, render_template

bp = Blueprint('/', __name__,)


@bp.route('/')
def index():
    return render_template('index.html')
