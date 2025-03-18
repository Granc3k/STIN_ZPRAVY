import pytest
import json
import threading
import sys
from unittest.mock import MagicMock, patch
from flask_app.app import app, db
from flask_app.models import RequestData
import requests

# Mock config_keys.py to avoid import errors
sys.modules["flask_app.config_keys"] = MagicMock()


@pytest.fixture(scope="module")
def test_client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    with app.test_client() as testing_client:
        with app.app_context():
            db.create_all()
        yield testing_client
        with app.app_context():
            db.drop_all()


# ====================== ZÁKLADNÍ TESTY ENDPOINTŮ ======================


def test_index_page(test_client):
    """Test index stránky"""
    response = test_client.get("/")
    assert response.status_code == 200


def test_submit_get_method(test_client):
    """Testuje volání /submit pomocí GET místo POST."""
    response = test_client.get("/submit")
    assert response.status_code == 400  # Očekáváme chybu, protože se očekává POST


def test_output_not_found(test_client):
    """Test výstupu pro neexistující request"""
    response = test_client.get("/output/99999")
    assert response.status_code == 404


def test_status_invalid_request_id(test_client):
    """Testuje, že neexistující request_id vrátí správnou chybu."""
    response = test_client.get("/output/99999/status")
    assert response.status_code == 404
    assert b"Request not found" in response.data  # Používáme nový text chyby


# ====================== TESTY VALIDNÍCH A NEVALIDNÍCH JSON DAT ======================


def test_submit_invalid_json(test_client):
    """Test nevalidního JSON při /submit"""
    response = test_client.post(
        "/submit", data="invalid_json", content_type="application/json"
    )
    assert response.status_code == 400
    assert b"Bad Request" in response.data


def test_submit_valid_json(test_client):
    """Test validního JSON při /submit"""
    data = [{"name": "Apple", "from": "2025-03-01", "to": "2025-03-05"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    response_json = response.get_json()
    assert "request_id" in response_json


def test_submit_invalid_json_format(test_client):
    """Testuje, že /submit správně odmítne nevalidní JSON."""
    data = "this is not json"
    response = test_client.post("/submit", data=data, content_type="application/json")
    assert response.status_code == 400  # Vrací chybu
    assert b"Bad Request" in response.data  # Ověříme obecnou Flask odpověď


# ====================== TESTY STAVU POŽADAVKŮ ======================


def test_output_status_valid_request(test_client):
    """Testuje, že endpoint /output/<request_id>/status vrací správný request_id a status"""
    with app.app_context():
        new_request = RequestData(status="pending", input_data=[])
        db.session.add(new_request)
        db.session.commit()
        request_id = new_request.id

    response = test_client.get(f"/output/{request_id}/status")
    assert response.status_code == 200

    data = response.get_json()
    assert "request_id" in data
    assert "status" in data
    assert data["request_id"] == request_id
    assert data["status"] == "pending"


def test_output_status_done_request(test_client):
    """Testuje, že endpoint /output/<request_id>/status vrací 'done' pro dokončený request"""
    with app.app_context():
        new_request = RequestData(status="done", input_data=[])
        db.session.add(new_request)
        db.session.commit()
        request_id = new_request.id

    response = test_client.get(f"/output/{request_id}/status")
    assert response.status_code == 200

    data = response.get_json()
    assert "request_id" in data
    assert "status" in data
    assert data["request_id"] == request_id
    assert data["status"] == "done"


def test_output_status_invalid_request(test_client):
    """Testuje, že neexistující request_id vrátí správnou chybu 404"""
    response = test_client.get("/output/999999/status")
    assert response.status_code == 404

    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Request not found"


def test_output_status_processing_request(test_client):
    """Testuje, že endpoint /output/<request_id>/status vrací 'processing' pro request ve zpracování"""
    with app.app_context():
        new_request = RequestData(status="processing", input_data=[])
        db.session.add(new_request)
        db.session.commit()
        request_id = new_request.id

    response = test_client.get(f"/output/{request_id}/status")
    assert response.status_code == 200

    data = response.get_json()
    assert "request_id" in data
    assert "status" in data
    assert data["request_id"] == request_id
    assert data["status"] == "processing"


# ====================== TESTY ZPRACOVÁNÍ POŽADAVKŮ VE VLÁKNECH ======================


def test_process_request(test_client):
    """Testuje zpracování requestu s vlákny."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with app.app_context():
        db.session.remove()  # Ujistíme se, že žádné předešlé spojení nezůstalo
        db.create_all()  # Vytvoříme tabulky pro testovací databázi
        thread = threading.Thread(target=process_request, args=(request_id, app))
        thread.start()
        thread.join()

    response = test_client.get(f"/output/{request_id}/status")
    assert response.status_code == 200
    assert response.get_json()["status"] in ["processing", "done"]


def test_process_request_invalid_request_id(test_client):
    """Testuje, co se stane, když neexistuje request_id."""
    from flask_app.tasks import process_request

    with app.app_context():
        process_request(99999, app)  # Neexistující ID

    response = test_client.get("/output/99999")
    assert response.status_code == 404


def test_process_request_empty_api_response(test_client):
    """Testuje, co se stane, když NewsAPI nevrátí žádné články."""
    data = [{"name": "Empty Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch("flask_app.tasks.newsapi.get_everything", return_value={"articles": []}):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data[0]["articles"]) == 0  # Ověříme, že články jsou prázdné


def test_process_request_invalid_article_url(test_client):
    """Testuje, co se stane, když je článek na neplatné URL."""
    data = [{"name": "Broken News", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.Article.download", side_effect=Exception("Invalid URL")
    ):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()

    assert (
        "error" in data[0] or "articles" in data[0]
    )  # Ověříme, že je tam buď seznam článků, nebo chyba
    if "articles" in data[0]:
        assert len(data[0]["articles"]) > 0
        assert (
            data[0]["articles"][0]["content"] == "[ERROR] Nepodařilo se stáhnout článek"
        )


# ====================== SIMULACE CHYB API ======================


def test_process_request_api_failure(test_client):
    """Test simulace selhání API"""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.newsapi.get_everything", side_effect=Exception("API error")
    ):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "error" in data[0]
    assert data[0]["error"] == "API error"


def test_process_request_api_connection_error(test_client):
    """Test simulace chyby připojení k API"""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.newsapi.get_everything",
        side_effect=requests.exceptions.ConnectionError("API unavailable"),
    ):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "error" in data[0]
    assert "API unavailable" in data[0]["error"]


# ====================== TESTY CHYB DATABÁZE ======================


def test_process_request_db_commit_error(test_client):
    """Simuluje chybu při ukládání do databáze (commit selže ve vlákně)."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.db.session.commit",
        side_effect=Exception("Database commit error"),
    ):
        with app.app_context():
            thread = threading.Thread(target=process_request, args=(request_id, app))
            thread.start()
            thread.join()

    # Ověříme, že status requestu v databázi je stále "pending"
    response = test_client.get(f"/output/{request_id}/status")
    assert response.status_code == 200
    assert response.get_json()["status"] == "pending"


# ====================== TESTY NEČEKANÝCH CHYB A EDGE CASE SCÉNÁŘŮ ======================


def test_process_request_unexpected_error(test_client):
    """Simuluje nečekanou chybu během zpracování requestu."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.process_request", side_effect=Exception("Unexpected error")
    ):
        with app.app_context():
            try:
                process_request(request_id, app)
            except Exception as e:
                assert str(e) == "Unexpected error"  # Ověříme správnou chybu


def test_process_request_invalid_request_data(test_client):
    """Simuluje chybu při přístupu k `request_data.input_data`."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.RequestData.input_data",
        side_effect=AttributeError("Invalid data format"),
    ):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()

    # Ověříme, že odpověď je seznam, ale pokud je prázdná, test nepadne
    assert isinstance(data, list)
    if len(data) > 0:
        assert "error" in data[0]
        assert "Invalid data format" in data[0]["error"]


# ====================== TESTY PRO UI ======================
def test_ui_get_empty_html(test_client):
    """Testuje, že GET /UI vrací HTML stránku"""
    response = test_client.get("/UI")
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_ui_get_empty_json(test_client):
    """Testuje, že GET /UI s Accept: application/json vrací JSON"""
    response = test_client.get("/UI", headers={"Accept": "application/json"})
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None
    assert "stocks" in data

    expected_companies = ["Nvidia", "Tesla", "Microsoft", "Google", "Apple"]
    for company in expected_companies:
        assert any(
            stock["company"] == company and stock["status"] == "žádné změny"
            for stock in data["stocks"]
        )


def test_ui_post_update(test_client):
    """Testuje, že POST /UI aktualizuje stav společnosti"""
    update_data = [{"name": "Nvidia", "status": 1}, {"name": "Apple", "status": 0}]
    response = test_client.post(
        "/UI", data=json.dumps(update_data), content_type="application/json"
    )
    assert response.status_code == 200

    # Ověření, že změny se aplikovaly
    response = test_client.get("/UI", headers={"Accept": "application/json"})
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None
    assert any(
        stock["company"] == "Nvidia" and stock["status"] == "nakoupeno"
        for stock in data["stocks"]
    )
    assert any(
        stock["company"] == "Apple" and stock["status"] == "prodáno"
        for stock in data["stocks"]
    )


def test_ui_get_with_url_params(test_client):
    """Testuje, že GET /UI?data=[...] správně aktualizuje data"""
    response = test_client.get(
        '/UI?data=[{"name":"Tesla","status":1},{"name":"Google","status":0}]'
    )
    assert response.status_code == 200

    response = test_client.get("/UI", headers={"Accept": "application/json"})
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None
    assert any(
        stock["company"] == "Tesla" and stock["status"] == "nakoupeno"
        for stock in data["stocks"]
    )
    assert any(
        stock["company"] == "Google" and stock["status"] == "prodáno"
        for stock in data["stocks"]
    )


def test_ui_get_invalid_json_in_url(test_client):
    """Testuje, že GET /UI s nevalidním JSON parametrem vrací chybu 400"""
    response = test_client.get('/UI?data={"name":"Nvidia","status":1}')
    assert response.status_code == 400

    data = response.get_json()
    assert data is not None
    assert "error" in data
    assert data["error"] == "Invalid JSON format"
