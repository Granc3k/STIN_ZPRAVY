import requests
from newsapi import NewsApiClient
from database import db
from models import RequestData
from config import NEWS_API_KEY  # Načtení API klíče

newsapi = NewsApiClient(api_key=NEWS_API_KEY)


def process_request(request_id):
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
            print(f"[INFO] Nalezeno {len(articles_list)} zpráv pro {company['name']}.")

            results.append({"company": company["name"], "articles": articles_list})
        except Exception as e:
            print(f"[ERROR] Chyba při získávání zpráv pro {company['name']}: {e}")
            results.append({"company": company["name"], "error": str(e)})

    # Výpis zpracovaných dat do konzole
    print(f"\n[INFO] Zpracovaná data pro request ID {request_id}:")
    for result in results:
        print(f" - {result['company']}: {len(result.get('articles', []))} zpráv")

    # Uložení výstupu do DB
    request_data = db.session.get(RequestData, request_id)  # Opětovné načtení objektu
    request_data.processed_data = results  # Uložení odpovědi API
    request_data.status = "done"
    db.session.commit()

    print(f"[INFO] Request ID {request_id} byl úspěšně zpracován.\n")
