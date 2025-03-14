import os

# Preferujeme načítání API klíče z prostředí (produkce, GitHub Actions)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not NEWS_API_KEY:
    try:
        from flask_app import config_keys
        NEWS_API_KEY = config_keys.NEWS_API_KEY
    except ImportError:
        NEWS_API_KEY = None  # Bezpečný fallback
        print("[WARNING] NEWS_API_KEY není nastaven. Aplikace nemusí správně fungovat.")

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
