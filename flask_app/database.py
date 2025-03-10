from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    app.config.from_object("flask_app.config")
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Vytvoření tabulek při spuštění aplikace
