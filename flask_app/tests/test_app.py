import pytest
import json
import threading
import sys
from unittest.mock import MagicMock, patch
from flask_app.app import app, db
from flask_app.models import RequestData
import requests
import os
from datetime import datetime, timedelta

# ====================== MOCKOVÁNÍ CONFIGŮ ======================


sys.modules["flask_app.config_keys"] = MagicMock()


# ====================== PODPŮRNÉ FCE ======================


def _get_dynamic_dates():
    today = datetime.utcnow().date()
    two_weeks_ago = today - timedelta(days=14)
    return str(two_weeks_ago), str(today)


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
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Empty Company", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch("flask_app.tasks.newsapi.get_everything", return_value={"articles": []}):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["company_name"] == "Empty Company"
    assert data[0]["rating"] is None


def test_process_request_invalid_article_url(test_client):
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Broken News", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.Article.download", side_effect=Exception("Invalid URL")
    ):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200


# ====================== SIMULACE CHYB API ======================


def test_process_request_api_failure(test_client):
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Test Company", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.newsapi.get_everything", side_effect=Exception("API error")
    ):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["company_name"] == "Test Company"
    assert data[0]["rating"] is None


def test_process_request_api_connection_error(test_client):
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Test Company", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.newsapi.get_everything",
        side_effect=requests.exceptions.ConnectionError("API unavailable"),
    ):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["company_name"] == "Test Company"
    assert data[0]["rating"] is None


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
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Test Company", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.utils.news_rating.NewsRating.rate_news",
        side_effect=Exception("Unexpected error"),
    ):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["company_name"] == "Test Company"
    assert data[0]["rating"] is None


def test_process_request_invalid_request_data(test_client):
    from_date, to_date = _get_dynamic_dates()
    data = [{"name": "Test Company", "from": from_date, "to": to_date}]
    response = test_client.post(
        "/submit", data=json.dumps(data), content_type="application/json"
    )
    request_id = response.get_json()["request_id"]

    from flask_app.tasks import process_request

    with patch(
        "flask_app.tasks.RequestData.input_data",
        side_effect=AttributeError("Invalid data format"),
    ):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "fake-key"}):
            with app.app_context():
                process_request(request_id, app)

    response = test_client.get(f"/output/{request_id}")
    assert response.status_code in [200, 404]


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


# ====================== TESTY NewsRating ======================

from flask_app.utils.news_rating import NewsRating
from unittest.mock import MagicMock


@pytest.fixture
def sample_news_json():
    return json.dumps(
        [
            "Apple releases new product.",
            "Tesla delays delivery.",
            "Google reports strong earnings.",
        ]
    )


def test_parse_json_news_valid(sample_news_json):
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        result = rater.parse_json_news(sample_news_json)
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)


def test_parse_json_news_invalid_format():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        with pytest.raises(ValueError):
            rater.parse_json_news("not a json")


def test_check_news_count_limit():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        assert rater.check_news_count(["x"] * 10)
        assert not rater.check_news_count(["x"] * 20)


def test_check_news_length_limit():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        short_news = ["short"] * 5
        long_news = ["a" * 1200]
        assert rater.check_news_length(short_news)
        assert not rater.check_news_length(long_news)


def test_limit_news_count_functionality():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        items = [f"news {i}" for i in range(20)]
        result = rater.limit_news_count(items)
        assert len(result) == rater.max_news_count


def test_truncate_news_functionality():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        input_data = ["x" * 1100, "ok"]
        result = rater.truncate_news(input_data)
        assert result[0] == "x" * rater.max_news_length
        assert result[1] == "ok"


def test_validate_news_combination():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        short = ["aaa"] * 5
        long = ["x" * 2000] * 5
        too_many = ["text"] * 20

        assert rater.validate_news(short) == (True, True)
        assert rater.validate_news(long) == (True, False)
        assert rater.validate_news(too_many) == (False, True)


def test_parse_openai_response_valid_json():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"0": 6.5, "1": 3.2}'
        result = rater.parse_openai_response(mock_response)
        assert isinstance(result, dict)
        assert result[0] == 6.5
        assert result[1] == 3.2


def test_parse_openai_response_invalid_json():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "NOT JSON"
        with pytest.raises(ValueError):
            rater.parse_openai_response(mock_response)


def test_parse_openai_response_out_of_range():
    with patch.dict(os.environ, {"OPEN_AI_API_KEY": "mock-key"}):
        rater = NewsRating()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"0": 20}'
        with pytest.raises(ValueError):
            rater.parse_openai_response(mock_response)
