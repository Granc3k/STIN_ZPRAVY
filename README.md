**Semestrální práce předmětu STIN - modul Zprávy**

- Martin "Granc3k" Šimon, Jakub Koněrza

## Framework

- Flask

## Konfigurace

**init prostředí - musí se v root složce pro tenhle projekt:**

### Windows
- `py -3 -m venv .venv`
- `.\.venv\Scripts\activate`
- `pip install Flask`

#### Pokud nefachčí
- `Set-ExecutionPolicy Unrestricted -Scope CurrentUser`

nebo

- `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`


### macOS
- `python3 -m venv .venv`
- `. .venv/bin/activate`
- `pip install Flask`



**Kdyby se něco pokazilo ve virt. prostředí:**

***Dependencies:***
- pip install Werkzeug
- pip install Jinja2
- pip install -U MarkupSafe
- pip install -U itsdangerous
- pip install click
- pip install blinker


- Tohle by spíš chtělo requirements.txt

***Optional dependencies:***
- pip install python-dotenv
- pip install watchdog
