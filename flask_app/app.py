import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_app.database import db, init_db
from flask_app.models import RequestData
from flask_app.tasks import process_request
import threading
from datetime import datetime


app = Flask(__name__)
init_db(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST", "GET"])
def submit():
    """
    Zpracuje vstupní data přes POST nebo GET a spustí asynchronní zpracování požadavku.

    Pro POST:
    - Očekává JSON data v těle požadavku
    Pro GET:
    - Očekává URL parametr 'data' obsahující JSON řetězec

    Args:
        N/A (přijímá data přes request.json pro POST nebo request.args pro GET)

    Returns:
        Pro POST:
            JSON: {"request_id": <id>} se status code 200
        Pro GET:
            Redirect na /status endpoint s request_id

    Raises:
        400 Bad Request:
            - Pokud chybí JSON data (POST)
            - Pokud chybí parametr 'data' (GET)
            - Pokud data nejsou validní JSON

    Examples:
        POST request:
        curl -X POST -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:5000/submit

        GET request:
        http://localhost:5000/submit?data={"key":"value"}

    Poznámky:
        - Požadavek je zpracován asynchronně v background threadu
        - Vytvoří nový záznam v DB se statusem 'pending'
        - Pro sledování stavu použijte /status endpoint s vráceným request_id
    """

    # nacteni dat do promenne "data"
    if request.method == "POST":
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400
    else:
        data_param = request.args.get("data")
        if not data_param:
            return jsonify({"error": "Missing data parameter"}), 400
        try:
            data = json.loads(data_param)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format"}), 400

    print(f"[DEBUG] Přijatá data: {data}")
    # predani promenne "data" do tasks.py
    with app.app_context():
        new_request = RequestData(
            status="pending", input_data=data
        )  # vytvoreni prvku v databazi
        db.session.add(new_request)  # pridani prvku do databaze
        db.session.commit()  # ulozeni zmen do databaze
        request_id = new_request.id  # ziskani ID noveho prvku v databazi

    # spusteni noveho vlakna s funkci process_request v tasks.py
    threading.Thread(target=process_request, args=(request_id, app)).start()

    # pokud je metoda GET, presmeruje na /status endpoint s request_id
    if request.method == "GET":
        return redirect(url_for("get_status", request_id=request_id))
    # pokud je metoda POST, vrati JSON s request_id
    else:
        return jsonify({"request_id": request_id})


@app.route("/output/<int:request_id>/status", methods=["GET"])
def get_status(request_id):
    with app.app_context():
        # vezme data z databáze k IDcku v URL a printne status zpracovani
        request_data = db.session.get(RequestData, request_id)
        if not request_data:
            return jsonify({"error": "Request not found"}), 404
        return jsonify(
            {
                "request_id": request_id,  # Přidání ID requestu do odpovědi - pro GET metodu u defaultni stranky
                "status": request_data.status,
            }
        )


@app.route("/output/<int:request_id>/all", methods=["GET"])
def get_all_request_data(request_id):
    with app.app_context():
        # vezme data z databáze a prostě všecko vyprintí v jsonu
        request_data = db.session.get(RequestData, request_id)
        if not request_data:
            return jsonify({"error": "Request not found"}), 404

        return jsonify(
            {
                "request_id": request_data.id,
                "status": request_data.status,
                "input_data": request_data.input_data,
                "news_data": request_data.news_data,
                "sentiment_data": request_data.sentiment_data,
            }
        )


@app.route("/output/<int:request_id>", methods=["GET"])
def get_output(request_id):
    with app.app_context():
        # vezme data z databáze a vrátí vyhodnocená data pro daný request
        request_data = db.session.get(RequestData, request_id)
        if not request_data or request_data.status != "done":
            return jsonify({"error": "Data not ready"}), 404

        print(f"[DEBUG] Typ sentiment_data: {type(request_data.sentiment_data)}")
        print(f"[DEBUG] Hodnota sentiment_data: {request_data.sentiment_data}")

        # Vrácení dat ve správném formátu
        return jsonify(request_data.sentiment_data)


# Předdefinované společnosti
ALLOWED_COMPANIES = ["Nvidia", "Tesla", "Microsoft", "Google", "Apple"]

# Paměťová proměnná pro stav akcií (inicializováno jako "žádné změny" s časem "Nikdy")
stock_data = {
    company: {"status": "žádné změny", "updated_at": "Nikdy"}
    for company in ALLOWED_COMPANIES
}


@app.route("/UI", methods=["GET", "POST"])
def ui_page():
    if request.method == "POST" or request.args.get("data"):
        try:
            if request.method == "POST":
                data = request.get_json()
            else:  # Pokud GET obsahuje ?data=[...]
                data_param = request.args.get("data")
                data = json.loads(data_param) if data_param else None

            if not isinstance(data, list):  # Musí to být seznam slovníků
                raise ValueError("Invalid JSON format")

        except (json.JSONDecodeError, ValueError, TypeError):
            return jsonify({"error": "Invalid JSON format"}), 400

        for entry in data:
            if not isinstance(entry, dict):
                return jsonify({"error": "Invalid data format"}), 400

            company_name = entry.get("name")
            status = entry.get("status")
            # přiřazení statusu a času změny akcií
            if company_name in ALLOWED_COMPANIES and status in [0, 1]:
                stock_data[company_name]["status"] = (
                    "nakoupeno" if status == 1 else "prodáno"
                )
                stock_data[company_name]["updated_at"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        return jsonify({"message": "Data updated successfully"})

    # Odpověď ve formátu JSON pokud je požadováno
    if request.headers.get("Accept") == "application/json":
        return jsonify(
            {
                "stocks": [
                    {
                        "company": company,
                        "status": data["status"],
                        "updated_at": data["updated_at"],
                    }
                    for company, data in stock_data.items()
                ]
            }
        )

    # Jinak HTML stránka
    display_data = {
        "stocks": [
            {
                "company": company,
                "status": data["status"],
                "updated_at": data["updated_at"],
            }
            for company, data in stock_data.items()
        ]
    }
    return render_template("ui.html", data=display_data)
