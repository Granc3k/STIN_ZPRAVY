# Semestrální práce předmětu STIN - modul Zprávy

| Tým                           |
|:-----------------------------:|
| Martin "Granc3k" Šimon         |
| Jakub "Sýcockrka" Koněrza      |
| Matěj "REM" Retych              |


[![codecov](https://codecov.io/gh/Granc3k/STIN_ZPRAVY/graph/badge.svg?token=AO8L02LX7E)](https://codecov.io/gh/Granc3k/STIN_ZPRAVY)

<p align="center">
  <strong><a href="https://stin-zpravy.azurewebsites.net/">Odkaz na nasazené řešení</a> 📊</strong>
</p>


## Tech Stack

- **Backend:** Flask  
- **Frontend:** HTML 🎨  
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

## Komunikace
![diagram](./Dokumentace/komunikace.svg)

## Používání aplikace

### 1. Zadávání dat ke zpracování
- Úvodní stránka slouží k zadání JSON dat pro zpracování.
- Data lze odeslat pomocí URL parametrů: ```/submit?data="[JSON_DATA]"```

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


## Spouštění testů
```bash
pytest --cov=flask_app flask_app/tests/
```


## Endpointy

| Endpoint                  | Popis                                         |
|---------------------------|----------------------------------------------|
| `/`                       | Výchozí stránka pro zadávání dat ke zpracování zpráv |
| `/output/<ID_requestu>`   | Zobrazení zpracovaných dat                   |
| `/output/<ID_requestu>/status` | Zobrazení stavu zpracování dat        |
| `/output/<ID_requestu>/all` | Zobrazení veškerých dat k danému requestu        |
| `/UI`                     | Zobrazení portfolia                               |


## Ukázka vzorových dat
- pro posílaných dat na zpracování:
- pro nejlepší výsledek žádejte o zpracování dat maximálně 2-3 týdny zpětně od vašeho aktuálního datumu - jinak se může stát že API nedokáže vzít data

```json
[
  {
    "name": "Nvidia",
    "from": "2025-03-04",
    "to": "2025-03-10"
  },
  {
    "name": "Microsoft",
    "from": "2025-03-04",
    "to": "2025-03-10"
  },
  {
    "name": "Apple",
    "from": "2025-03-04",
    "to": "2025-03-10"
  },
  {
    "name": "Google",
    "from": "2025-03-04",
    "to": "2025-03-10"
  },
  {
    "name": "Amazon",
    "from": "2025-03-04",
    "to": "2025-03-10"
  }
]

```


- pro posílání dat na prodej/koupi na endpointu /UI:
```json
[
    {"name": "Nvidia", "status": 0},
    {"name": "Apple", "status": 1},
    {"name":"Google", "status":0}
]
```


