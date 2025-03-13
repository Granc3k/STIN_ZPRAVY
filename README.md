# Semestrální práce předmětu STIN - modul Zprávy

- Martin "Granc3k" Šimon, Jakub Koněrza, Matěj Retych

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

## Používání aplikace
- Úvodní strana je pro zadávání json dat, které chcete zpracovat
    - Data se dají zadat přes URL parametry pomocí: **"SERVER_URL"/submit?data="JSON_DATA"**
- Po zadání dat se vygeneruje ID requestu a zobrazí se Vám na stránce. Pod tímto IDčkem následně naleznete svá zpracovaná data na **"SERVER_URL"/output/"ID_requestu"**
    -   Data se chvíli budou zpracovávat, tudíž pro kontrolování stavu zpracování dat kontrolujte **"SERVER_URL"/output/"ID_requestu"/status**. Stavy jso **done, pending**
- Pro zadání dat na prodej/koupi akcii využijte endpoint **"SERVER_URL"/UI**. Data se zde dají zadávat pomocí automaticky pomocí parametru v URL **"SERVER_URL"/UI?data="JSON DATA"**

- Veškeré formáty Json dat jsou k nalezení na samotných endpointech aplikace.


## Endpointy
- / - defaultní strana pro zadávání dat na zpracování zpráv
- /output/ID_requestu - vypisování zpracovaných dat
- /output/ID_requestu/status - vypisování stavu zpracování dat
- /UI - vypisování portfólia
