from os import getenv

from flask import Flask

from game_lists_site.__init__ import app
from game_lists_site.views import api, root


def main():
    app.run()

if __name__ == '__main__':
    main()
