from flask_app.database import db
from flask_sqlalchemy import SQLAlchemy


class RequestData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="pending")
    input_data = db.Column(db.JSON)
    processed_data = db.Column(db.JSON, nullable=True)
