# Semestrální práce předmětu STIN - modul Zprávy

- Martin "Granc3k" Šimon, Jakub Koněrza, Matěj Retych,

[![codecov](https://codecov.io/gh/Granc3k/STIN_ZPRAVY/graph/badge.svg?token=AO8L02LX7E)](https://codecov.io/gh/Granc3k/STIN_ZPRAVY)

**[ODKAZ NA SERVER](https://stin-zpravy.azurewebsites.net/)**  


## Tech Stack

- **Backend:** Flask  
- **Frontend:** HTML + CSS 🎨  
- **Analýza zpráv:** OpenAI GPT-4o-mini  

## Konfigurace

### Windows
```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
flask --app ./flask_app/app.py run
```
Pokud něco nefunguje:
- ```Set-ExecutionPolicy Unrestricted -Scope CurrentUser```
- ```Set-ExecutionPolicy RemoteSigned -Scope CurrentUser```

### macOS
```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
flask --app ./flask_app/app.py run
```

## Závislosti

```bash
pip install -r requirements.txt
```

```bash
pip install newspaper3k lxml[html_clean] flask-sqlalchemy newsapi-python Flask Werkzeug Jinja2 -U MarkupSafe -U itsdangerous click blinker python-dotenv watchdog
```

## Návrh zpracování
![diagram](./Dokumentace/navrh_zpracovani.svg)

## Používání aplikace

### 1. Zadávání dat ke zpracování
- Úvodní stránka slouží k zadání JSON dat pro zpracování.
- Data lze odeslat pomocí URL parametrů: ```/submit?data="[JSON_DATA]```

### 2. Získání zpracovaných dat
- Po zadání dat se vygeneruje **ID requestu**, které se zobrazí na stránce.
- Výsledky zpracování naleznete na následujícím endpointu: ```/output/[ID_requestu]```

Zpracování může chvíli trvat. Stav zpracování lze zkontrolovat zde: ```/output/[ID_requestu]/status```

Možné stavy:  
- `done` – zpracování dokončeno  
- `pending` – zpracování probíhá  

### 3. Zadání dat pro obchodování s akciemi
- Pro zadání dat na **prodej/koupi akcií** využijte tento endpoint: ```/UI```
- Data lze odeslat i automaticky přes URL parametr: ```/UI?data=[JSON_DATA]```


### 4. Formát JSON dat
- Formáty všech podporovaných JSON struktur jsou k dispozici přímo na jednotlivých endpointech aplikace.





## Endpointy

| Endpoint                  | Popis                                         |
|---------------------------|----------------------------------------------|
| `/`                       | Výchozí stránka pro zadávání dat ke zpracování zpráv |
| `/output/<ID_requestu>`   | Zobrazení zpracovaných dat                   |
| `/output/<ID_requestu>/status` | Zobrazení stavu zpracování dat        |
| `/UI`                     | Zobrazení portfolia                          |



