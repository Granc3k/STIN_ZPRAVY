import os
from flask_app import config_keys

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
NEWS_API_KEY = config_keys.NEWS_API_KEY
# NEWS_API_KEY = secrets.NEWS_API_KEY
