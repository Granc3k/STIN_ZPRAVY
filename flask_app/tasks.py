import json

import requests
import threading
from flask import current_app
from newsapi import NewsApiClient
from newspaper import Article  # Knihovna na stahování článků
from flask_app.database import db
from flask_app.models import RequestData
from flask_app.config import NEWS_API_KEY, LIST_SIZE  # Načtení API klíče
from sqlalchemy import create_engine

from flask_app.utils.news_rating import NewsRating

newsapi = NewsApiClient(api_key=NEWS_API_KEY)


def process_request(request_id, app):
    """
    Zpracuje požadavek na získání, analýzu a hodnocení zpráv pro více společností.

    Tato funkce provádí následující kroky:
    1. Vytvoří nové připojení k databázi v kontextu aplikace
    2. Načte data požadavku z databáze pomocí poskytnutého request_id
    3. Aktualizuje stav požadavku na "processing"
    4. Pro každou společnost ve vstupních datech:
       - Získá zprávy pomocí NewsAPI
       - Stáhne a zpracuje plný obsah každého článku
       - Formátuje a ukládá informace o článku
    5. Vypočítá hodnocení sentimentu zpráv pomocí NewsRating
    6. Uloží výsledky sentimentu do databáze
    7. Aktualizuje stav požadavku na "done"

    Parametry:
        request_id (int): Jedinečný identifikátor požadavku ke zpracování
        app (Flask): Instance Flask aplikace pro vytvoření kontextu

    Návratová hodnota:
        None

    Vedlejší efekty:
        - Aktualizuje stav požadavku v databázi
        - Ukládá výsledky analýzy sentimentu do databáze
        - Vypisuje zprávy o průběhu a chybové hlášky do konzole

    Výjimky:
        - Ošetřuje výjimky během získávání zpráv a analýzy sentimentu,
          zaznamenává chyby, ale pokračuje ve zpracování pro ostatní společnosti
    """
    with app.app_context():
        db.session.remove()  # Odstranění starého DB session
        db.engine.dispose()  # Uvolnění starého připojení (novější verze Flask-SQLAlchemy)

        # BYLO VYTVOŘENO KVŮLI TESTŮM - IDK UŽ ASI NENÍ TŘEBA
        # Ručně vytvoří nové připojení ke sdílené test.db
        # engine = create_engine("sqlite:///database.db", connect_args={"check_same_thread": False})
        # conn = engine.connect()
        # conn.exec_driver_sql("PRAGMA foreign_keys=ON;")  # Pokud používáš cizí klíče
        # conn.close()

        db.create_all()  # Zajištění, že tabulka request_data existuje i ve vlákně

        # Informace o requestu se předávají pomocí ID v databázi
        request_data = db.session.get(RequestData, request_id)
        if not request_data:
            print(f"[ERROR] Request ID {request_id} nebyl nalezen v databázi.")
            return

        # Výpis vstupních dat do konzole
        print(f"\n[INFO] Zpracovávám request ID: {request_id}")
        print(f"[INFO] Vstupní data: {request_data.input_data}")

        # Aktualizace stavu na "processing"
        request_data.status = "processing"
        db.session.commit()

        results = []
        print(f"[DEBUG] request_data.input_data: {request_data.input_data}")
        # Postupné zpracování každé společnosti
        for company in request_data.input_data:
            print(f"\n[INFO] Získávám zprávy pro společnost: {company['name']}")
            try:
                articles = newsapi.get_everything(
                    q=company["name"],  # Název společnosti
                    from_param=company["from"],  # Datum "od"
                    to=company["to"],  # Datum "do"
                    language="en",
                    sort_by="relevancy",
                    page_size=LIST_SIZE,  # Omezení stažených stránek - najdeš v configu
                )

                if articles is None or "articles" not in articles:
                    raise ValueError(f"API nevrátilo žádná data pro {company['name']}.")

                articles_list = articles.get("articles", [])

                if not articles_list:
                    print(f"[WARNING] Nebyly nalezeny žádné zprávy pro {company['name']}.")

                formatted_articles = []
                for article in articles_list:
                    full_content = "[ERROR] Nepodařilo se stáhnout článek"
                    article_url = article.get("url", "")

                    if not article_url:
                        print(f"[WARNING] Článek bez platné URL, přeskočeno.")
                        continue  # Přeskočení nevalidního článku

                    try:
                        news_article = Article(article_url, language="en")
                        news_article.download()
                        news_article.parse()
                        full_content = news_article.text.strip() if news_article.text else full_content
                    except Exception as e:
                        print(f"[ERROR] Chyba při stahování článku {article_url}: {e}")

                    # Odstranění úvodu o autorovi článku
                    temp_text = full_content.split("\n\n")
                    if len(temp_text) > 1:
                        del temp_text[0]
                    formatted_content = " ".join(temp_text).strip()

                    formatted_articles.append(
                        {
                            "title": article.get("title", "Bez názvu"),
                            "url": article_url,
                            "publishedAt": article.get("publishedAt", "Neznámé datum"),
                            "source": article.get("source", {}).get("name", "Neznámý zdroj"),
                            "content": formatted_content,
                        }
                    )

                print(f"[INFO] Nalezeno {len(formatted_articles)} zpráv pro {company['name']}.")

                results.append({"company": company["name"], "articles": formatted_articles})

            except ValueError as ve:
                print(f"[ERROR] {ve}")
                results.append({"company": company["name"], "error": str(ve)})

            except Exception as e:
                print(f"[ERROR] Neočekávaná chyba při zpracování zpráv pro {company['name']}: {e}")
                results.append({"company": company["name"], "error": str(e)})

        # Výpis zpracovaných dat do konzole
        print(f"\n[INFO] Zpracovaná data pro request ID {request_id}:")
        for result in results:
            print(f" - {result['company']}: {len(result.get('articles', []))} zpráv")

        # NewsRating
        news_rater = NewsRating()
        sentiment_results = []

        for result in results:
            print(f"\n[INFO] Zpracovávám zprávy pro společnost: {result['company']}")
            try:
                if 'articles' in result and result['articles']:
                    # Extrakce textů článků pro danou společnost
                    news_texts = [
                        f"{article.get('title', '')} {article.get('content', '')}".strip()  # Spojení title a content
                        for article in result['articles']
                        if article.get('content')  # Zachováváme podmínku pro obsah
                    ]


                    if news_texts:
                        # Konverze seznamu zpráv na JSON řetězec
                        json_string = json.dumps(news_texts)

                        # Získání hodnocení přes NewsRating
                        average_rating = news_rater.rate_news(json_string)

                        # Uložení pouze názvu společnosti a hodnocení do výstupu
                        sentiment_results.append({
                            "company_name": result['company'],
                            "rating": average_rating
                        })

                        print(f"[INFO] Průměrné hodnocení pro {result['company']}: {average_rating}")
                    else:
                        print(f"[WARNING] Žádné textové obsahy pro hodnocení společnosti {result['company']}")
                        sentiment_results.append({
                            "company_name": result['company'],
                            "rating": None
                        })
                else:
                    print(f"[WARNING] Žádné články pro hodnocení společnosti {result['company']}")
                    sentiment_results.append({
                        "company_name": result['company'],
                        "rating": None
                    })
            except Exception as e:
                print(f"[ERROR] Chyba při zpracování hodnocení pro {result['company']}: {e}")
                sentiment_results.append({
                    "company_name": result['company'],
                    "rating": None
                })

        # Uložení výstupu do DB
        request_data = db.session.get(RequestData, request_id)
        for item in sentiment_results:
            if item["rating"] is not None:
                item["rating"] = float(item["rating"])  # Zajištění, že rating je float
        request_data.sentiment_data = sentiment_results
        request_data.status = "done"
        db.session.commit()

        print(f"[INFO] Request ID {request_id} byl úspěšně zpracován.\n")
