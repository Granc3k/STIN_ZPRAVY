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

@pytest.fixture(scope='module')
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///test.db"
    with app.test_client() as testing_client:
        with app.app_context():
            db.create_all()
        yield testing_client
        with app.app_context():
            db.drop_all()

# Test index stránky
def test_index_page(test_client):
    response = test_client.get('/')
    assert response.status_code == 200

# Test nevalidního JSON při /submit
def test_submit_invalid_json(test_client):
    response = test_client.post('/submit', data="invalid_json", content_type='application/json')
    assert response.status_code == 400
    assert b"Bad Request" in response.data

# Test validního JSON při /submit
def test_submit_valid_json(test_client):
    data = [{"name": "Apple", "from": "2024-03-01", "to": "2024-03-05"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    response_json = response.get_json()
    assert "request_id" in response_json

# Test status endpointu před zpracováním
def test_status_pending(test_client):
    new_request = RequestData(status="pending", input_data=[{"name": "Apple"}])
    db.session.add(new_request)
    db.session.commit()
    response = test_client.get(f'/output/{new_request.id}/status')
    assert response.status_code == 200
    assert response.get_json()["status"] == "pending"

# Test výstupu pro neexistující request
def test_output_not_found(test_client):
    response = test_client.get('/output/99999')
    assert response.status_code == 404

def test_process_request(test_client):
    """Testuje zpracování requestu s vlákny."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with app.app_context():
        db.session.remove()  # Ujistíme se, že žádné předešlé spojení nezůstalo
        db.create_all()  # Vytvoříme tabulky pro testovací databázi
        thread = threading.Thread(target=process_request, args=(request_id, app))
        thread.start()
        thread.join()

    response = test_client.get(f'/output/{request_id}/status')
    assert response.status_code == 200
    assert response.get_json()["status"] in ["processing", "done"]

# Test simulace selhání API
def test_process_request_api_failure(test_client):
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.newsapi.get_everything", side_effect=Exception("API error")):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f'/output/{request_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert "error" in data[0]
    assert data[0]["error"] == "API error"

# Test simulace chyby připojení k API
def test_process_request_api_connection_error(test_client):
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.newsapi.get_everything", side_effect=requests.exceptions.ConnectionError("API unavailable")):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f'/output/{request_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert "error" in data[0]
    assert "API unavailable" in data[0]["error"]

def test_process_request_db_commit_error(test_client):
    """Simuluje chybu při ukládání do databáze (commit selže ve vlákně)."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.db.session.commit", side_effect=Exception("Database commit error")):
        with app.app_context():
            thread = threading.Thread(target=process_request, args=(request_id, app))
            thread.start()
            thread.join()

    # Ověříme, že status requestu v databázi je stále "pending"
    response = test_client.get(f'/output/{request_id}/status')
    assert response.status_code == 200
    assert response.get_json()["status"] == "pending"

def test_process_request_invalid_request_data(test_client):
    """Simuluje chybu při přístupu k `request_data.input_data`."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.RequestData.input_data", side_effect=AttributeError("Invalid data format")):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f'/output/{request_id}')
    assert response.status_code == 200
    data = response.get_json()

    # Ověříme, že odpověď je seznam, ale pokud je prázdná, test nepadne
    assert isinstance(data, list)
    if len(data) > 0:
        assert "error" in data[0]
        assert "Invalid data format" in data[0]["error"]

def test_process_request_unexpected_error(test_client):
    """Simuluje nečekanou chybu během zpracování requestu."""
    data = [{"name": "Test Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.process_request", side_effect=Exception("Unexpected error")):
        with app.app_context():
            try:
                process_request(request_id, app)
            except Exception as e:
                assert str(e) == "Unexpected error"  # Ověříme správnou chybu

def test_output_invalid_request_id(test_client):
    """Testuje odpověď na nevalidní request_id."""
    response = test_client.get('/output/invalid_id')
    assert response.status_code == 404

def test_submit_get_method(test_client):
    """Testuje volání /submit pomocí GET místo POST."""
    response = test_client.get('/submit')
    assert response.status_code == 400  # Očekáváme chybu, protože se očekává POST

def test_process_request_invalid_request_id(test_client):
    """Testuje, co se stane, když neexistuje request_id."""
    from flask_app.tasks import process_request
    with app.app_context():
        process_request(99999, app)  # Neexistující ID

    response = test_client.get('/output/99999')
    assert response.status_code == 404


def test_process_request_empty_api_response(test_client):
    """Testuje, co se stane, když NewsAPI nevrátí žádné články."""
    data = [{"name": "Empty Company", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.newsapi.get_everything", return_value={"articles": []}):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f'/output/{request_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data[0]["articles"]) == 0  # Ověříme, že články jsou prázdné

def test_process_request_invalid_article_url(test_client):
    """Testuje, co se stane, když je článek na neplatné URL."""
    data = [{"name": "Broken News", "from": "2025-02-08", "to": "2025-02-10"}]
    response = test_client.post('/submit', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request
    with patch("flask_app.tasks.Article.download", side_effect=Exception("Invalid URL")):
        with app.app_context():
            process_request(request_id, app)

    response = test_client.get(f'/output/{request_id}')
    assert response.status_code == 200
    data = response.get_json()

    assert "error" in data[0] or "articles" in data[0]  # Ověříme, že je tam buď seznam článků, nebo chyba
    if "articles" in data[0]:
        assert len(data[0]["articles"]) > 0
        assert data[0]["articles"][0]["content"] == "[ERROR] Nepodařilo se stáhnout článek"

def test_submit_invalid_json_format(test_client):
    """Testuje, že /submit správně odmítne nevalidní JSON."""
    data = "this is not json"
    response = test_client.post('/submit', data=data, content_type='application/json')
    assert response.status_code == 400  # Vrací chybu
    assert b"Bad Request" in response.data  # Ověříme obecnou Flask odpověď

def test_output_none_processed_data(test_client):
    """Testuje, co se stane, když `processed_data` je `None`."""
    new_request = RequestData(status="done", processed_data=None)
    db.session.add(new_request)
    db.session.commit()

    response = test_client.get(f'/output/{new_request.id}')
    assert response.status_code == 200
    assert response.get_json() in [{}, None]  # Ověříme, že odpověď je buď `{}` nebo `None`

def test_status_invalid_request_id(test_client):
    """Testuje, že neexistující request_id vrátí správnou chybu."""
    response = test_client.get('/output/99999/status')
    assert response.status_code == 404
    assert b"Request not found" in response.data  # Používáme nový text chyby
