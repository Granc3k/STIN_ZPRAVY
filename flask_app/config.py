import os
import config_keys

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///data.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
NEWS_API_KEY = config_keys.NEWS_API_KEY
# NEWS_API_KEY = secrets.NEWS_API_KEY
