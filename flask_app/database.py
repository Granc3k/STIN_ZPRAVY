from flask import Flask, render_template, request, jsonify
from database import db, RequestData, init_db
from tasks import process_request

app = Flask(__name__)
app.config.from_object("config")

init_db(app)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    new_request = RequestData(status="pending", input_data=data)
    db.session.add(new_request)
    db.session.commit()
    
    process_request(new_request.id)  # Synchronous processing
    
    return jsonify({"request_id": new_request.id}), 202

@app.route("/output/<int:request_id>/status", methods=["GET"])
def get_status(request_id):
    request_data = RequestData.query.get(request_id)
    if not request_data:
        return jsonify({"error": "Request not found"}), 404
    return jsonify({"status": request_data.status})

@app.route("/output/<int:request_id>", methods=["GET"])
def get_output(request_id):
    request_data = RequestData.query.get(request_id)
    if not request_data or request_data.status != "done":
        return jsonify({"error": "Data not ready"}), 404
    return jsonify(request_data.processed_data)

if __name__ == "__main__":
    app.run(debug=True)