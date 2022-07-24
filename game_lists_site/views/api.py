from flask import jsonify, request

from game_lists_site.__init__ import app


@app.route('/api/add-user')
def add_user():
    if request.method == 'POST':
        steam_id = request.form['steamId']
    return jsonify({'tesk': 'ok'})
