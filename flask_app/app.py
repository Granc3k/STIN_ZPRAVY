import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_app.database import db, init_db
from flask_app.models import RequestData
from flask_app.tasks import process_request
import threading

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
        return jsonify({"status": request_data.status})


@app.route("/output/<int:request_id>", methods=["GET"])
def get_output(request_id):
    with app.app_context():
        request_data = db.session.get(RequestData, request_id)
        if not request_data or request_data.status != "done":
            return jsonify({"error": "Data not ready"}), 404
        return jsonify(request_data.processed_data)


if __name__ == "__main__":
    app.run(debug=True)
