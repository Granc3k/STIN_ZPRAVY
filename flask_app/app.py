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

    with app.app_context():
        new_request = RequestData(status="pending", input_data=data)
        db.session.add(new_request)
        db.session.commit()
        request_id = new_request.id

    threading.Thread(target=process_request, args=(request_id, app)).start()

    if request.method == "GET":
        return redirect(url_for("get_status", request_id=request_id))
    else:
        return jsonify({"request_id": request_id})


@app.route("/output/<int:request_id>/status", methods=["GET"])
def get_status(request_id):
    with app.app_context():
        request_data = db.session.get(RequestData, request_id)
        if not request_data:
            return jsonify({"error": "Request not found"}), 404
        return jsonify(
            {
                "request_id": request_id,  # Přidání ID requestu do odpovědi
                "status": request_data.status,
            }
        )


@app.route("/output/<int:request_id>", methods=["GET"])
def get_output(request_id):
    with app.app_context():
        request_data = db.session.get(RequestData, request_id)
        if not request_data or request_data.status != "done":
            return jsonify({"error": "Data not ready"}), 404
        return jsonify(request_data.processed_data)
    

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
