import requests
import threading
from flask import current_app
from newsapi import NewsApiClient
from newspaper import Article  # Knihovna na stahování článků
from database import db
from models import RequestData
from config_keys import NEWS_API_KEY  # Načtení API klíče

newsapi = NewsApiClient(api_key=NEWS_API_KEY)


def process_request(request_id, app):
    with app.app_context():

        # Načtení dat z databáze
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
                    page_size=5,  # Omezíme na 5 výsledků
                )
                articles_list = articles.get("articles", [])

                # Uložíme jen relevantní informace včetně STAŽENÍ CELÉHO OBSAHU
                formatted_articles = []
                for article in articles_list:
                    full_content = "[ERROR] Nepodařilo se stáhnout článek"
                    try:
                        news_article = Article(article.get("url"))
                        news_article.download()
                        news_article.parse()
                        full_content = news_article.text  # Celý text článku
                    except Exception as e:
                        print(f"[ERROR] Chyba při stahování článku: {e}")

                    formatted_articles.append(
                        {
                            "title": article.get("title"),
                            "description": article.get("description"),
                            "url": article.get("url"),
                            "publishedAt": article.get("publishedAt"),
                            "source": article.get("source", {}).get("name"),
                            "content": full_content,  # CELÝ TEXT článku místo oříznutého `content`
                        }
                    )

                    print(
                        f"[INFO] - Zapisovaná data {article.get('title')}, {article.get('description')}, {article.get('url')}, {article.get('publishedAt')}, {article.get('source', {}).get('name')}, {full_content[:200]}..."
                    )  # Výpis prvních 200 znaků obsahu

                print(
                    f"[INFO] Nalezeno {len(formatted_articles)} zpráv pro {company['name']}."
                )

                results.append(
                    {"company": company["name"], "articles": formatted_articles}
                )
            except Exception as e:
                print(f"[ERROR] Chyba při získávání zpráv pro {company['name']}: {e}")
                results.append({"company": company["name"], "error": str(e)})

        # Výpis zpracovaných dat do konzole
        print(f"\n[INFO] Zpracovaná data pro request ID {request_id}:")
        for result in results:
            print(f" - {result['company']}: {len(result.get('articles', []))} zpráv")

        # Uložení výstupu do DB
        request_data = db.session.get(
            RequestData, request_id
        )  # Opětovné načtení objektu
        request_data.processed_data = results  # Uložení odpovědi API
        request_data.status = "done"
        db.session.commit()

        print(f"[INFO] Request ID {request_id} byl úspěšně zpracován.\n")
