from game_lists_site.__init__ import app
from flask import jsonify


@app.route('/test')
def test():
    return jsonify({'tesk': 'ok'})
