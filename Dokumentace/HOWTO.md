# init prostředí - musí se v root složce pro tenhle projekt:

## Windows
- py -3 -m venv .venv
- ./.venv/Scripts/activate
- pip install Flask

## macOS
- python3 -m venv .venv
- . .venv/bin/activate
- pip install Flask

***Pokud nefachčí na Widlích:***
- Set-ExecutionPolicy Unrestricted -Scope CurrentUser

nebo

- Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

## Přidané knihovny nad rámec
- pip install flask-sqlalchemy
- pip install newsapi-python


# Spuštění
- ./.venv/Scripts/activate
- flask --app .\flask_app\app.py run


## Kdyby se něco pokazilo ve virt. prostředí s Flaskem:

***Dependencies:***
- pip install Werkzeug
- pip install Jinja2
- pip install -U MarkupSafe
- pip install -U itsdangerous
- pip install click
- pip install blinker

***Optional dependencies:***
- pip install python-dotenv
- pip install watchdog


