import requests
from database import db, RequestData

def process_request(request_id):
    request_data = RequestData.query.get(request_id)
    if not request_data:
        return

    request_data.status = "processing"
    db.session.commit()

    # Getnutí zpráv z API
    response1 = requests.post("TODO API", json=request_data.input_data)
    news_data = response1.json() if response1.status_code == 200 else {}

    # Zpracování dat
    # TODO: implementace dalších fcí na zpracování dat pomocí AI, bude se to tam vkládat posupně pro každou společnost ve for loopu

    # Uložit výstup do DB
    #request_data.processed_data = formatted_data
    #request_data.status = "done"
    #db.session.commit()
