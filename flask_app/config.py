import os

# Preferujeme načítání API klíče z prostředí (produkce, GitHub Actions)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not NEWS_API_KEY:
    try:
        import importlib
        config_keys = importlib.import_module("flask_app.config_keys")
        NEWS_API_KEY = config_keys.NEWS_API_KEY
    except ModuleNotFoundError:
        NEWS_API_KEY = None  # Bezpečný fallback
        print("[WARNING] Nepodařilo se načíst config_keys. Používám pouze NEWS_API_KEY z prostředí.")

# Databázová konfigurace
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
