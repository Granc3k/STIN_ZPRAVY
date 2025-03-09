# Semestrální práce předmětu STIN - modul Zprávy

- Martin "Granc3k" Šimon, Jakub Koněrza

## Framework

- Flask :)

## Konfigurace

### Windows
- py -3 -m venv .venv
- ./.venv/Scripts/activate
- pip install -r requirements.txt
- flask --app .\flask_app\app.py run

Pokud něco nefunguje:
- Set-ExecutionPolicy Unrestricted -Scope CurrentUser
- Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

### macOS
- python3 -m venv venv
- . venv/bin/activate
- pip install -r requirements.txt
- flask --app ./flask_app/app.py run

## Dependencies
- pip install newspaper3k
- pip install lxml[html_clean]
- pip install flask-sqlalchemy
- pip install newsapi-python
- pip install Flask
- pip install Werkzeug
- pip install Jinja2
- pip install -U MarkupSafe
- pip install -U itsdangerous
- pip install click
- pip install blinker
- pip install python-dotenv
- pip install watchdog

## Návrh zpracování
![diagram](./Dokumentace/navrh_zpracovani.svg)
