import os
from flask_app import config_keys

LIST_SIZE = 5  # Počet zpráv na stránku

# Preferujeme načítání API klíčů z prostředí (produkce, GitHub Actions)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")

if not NEWS_API_KEY or not OPEN_AI_API_KEY:
    try:
        import importlib

        config_keys = importlib.import_module("flask_app.config_keys")

        if not NEWS_API_KEY:
            NEWS_API_KEY = config_keys.NEWS_API_KEY
        if not OPEN_AI_API_KEY:
            OPEN_AI_API_KEY = config_keys.OPEN_AI_API_KEY

    except ModuleNotFoundError:
        print(
            "[WARNING] Nepodařilo se načíst config_keys. Používám pouze API klíče z prostředí."
        )
        NEWS_API_KEY = NEWS_API_KEY or None  # Fallback na None
        OPEN_AI_API_KEY = OPEN_AI_API_KEY or None  # Fallback na None

# Databázová konfigurace
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
NEWS_API_KEY = config_keys.NEWS_API_KEY
# NEWS_API_KEY = secrets.NEWS_API_KEY
