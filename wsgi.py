"""Entry point for the backend application."""

from flask_app import server
from flask_app.server import app as app
if __name__ == '__main__':
    server.main()
