"""Tests for the Flask webapp."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from webapp.app import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    monkeypatch.setenv("PEPPYRUS_API_KEY", "test-key")
    monkeypatch.setenv("PEPPOL_SENDER_ID", "0208:0123456789")
    monkeypatch.setenv("PEPPYRUS_BASE_URL", "https://api.test.peppyrus.be/v1")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_no_creds(monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    monkeypatch.delenv("PEPPYRUS_API_KEY", raising=False)
    monkeypatch.delenv("PEPPOL_SENDER_ID", raising=False)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _mock_session(method: str, status: int, json_payload: object) -> MagicMock:
    """Build a mock session whose .get() or .post() returns the given response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_payload
    mock_session = MagicMock()
    getattr(mock_session, method).return_value = mock_resp
    return mock_session


# ---------- GET / ----------


def test_index_returns_form(client: FlaskClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Invoice Composer" in body
    assert "Bill to" in body
    assert "line-items-body" in body


# ---------- /api/org-info ----------


@patch("peppol_sender.api._session")
def test_org_info_success(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    mock_session_fn.return_value = _mock_session(
        "get",
        200,
        {"name": "POCITO", "VAT": "BE0674415660"},
    )
    resp = client.get("/api/org-info")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "POCITO"


def test_org_info_missing_credentials(client_no_creds: FlaskClient) -> None:
    resp = client_no_creds.get("/api/org-info")
    assert resp.status_code == 500
    assert "Missing" in resp.get_json()["error"]


# ---------- /api/lookup ----------


@patch("peppol_sender.api._session")
def test_lookup_success(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    mock_session_fn.return_value = _mock_session(
        "get",
        200,
        {"participantId": "0208:be0123456789", "services": [{}]},
    )
    resp = client.get("/api/lookup?vatNumber=0123456789&countryCode=BE")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["participantId"] == "0208:be0123456789"


def test_lookup_missing_params(client: FlaskClient) -> None:
    resp = client.get("/api/lookup")
    assert resp.status_code == 400
    assert "required" in resp.get_json()["error"]


# ---------- /api/business-card ----------


@patch("peppol_sender.api._session")
def test_business_card_success(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    mock_session_fn.return_value = _mock_session(
        "get",
        200,
        [{"entities": [{"name": [{"name": "POCITO"}], "countryCode": "BE"}]}],
    )
    resp = client.get("/api/business-card?participantId=0208:be0674415660")
    assert resp.status_code == 200
    cards = resp.get_json()
    assert cards[0]["entities"][0]["name"][0]["name"] == "POCITO"


def test_business_card_missing_param(client: FlaskClient) -> None:
    resp = client.get("/api/business-card")
    assert resp.status_code == 400


# ---------- /api/validate ----------


_VALID_INVOICE = {
    "invoice_number": "INV-001",
    "issue_date": "2025-01-01",
    "due_date": "2025-02-01",
    "currency": "EUR",
    "seller": {
        "name": "Seller",
        "registration_name": "Seller BV",
        "endpoint_id": "0123456789",
        "endpoint_scheme": "0208",
        "country": "BE",
    },
    "buyer": {
        "name": "Buyer",
        "registration_name": "Buyer BV",
        "endpoint_id": "987654321",
        "endpoint_scheme": "0208",
        "country": "NL",
    },
    "lines": [{"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "E", "tax_percent": 0}],
}


def test_validate_passes_for_valid_invoice(client: FlaskClient) -> None:
    resp = client.post("/api/validate", json=_VALID_INVOICE)
    assert resp.status_code == 200
    assert resp.get_json() == {"rules": []}


def test_validate_returns_rules_for_empty_invoice(client: FlaskClient) -> None:
    resp = client.post("/api/validate", json={})
    assert resp.status_code == 200
    rules = resp.get_json()["rules"]
    assert len(rules) > 0
    assert any(r["type"] == "FATAL" for r in rules)


# ---------- /api/send ----------


@patch("peppol_sender.api._session")
def test_send_success(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    mock_session_fn.return_value = _mock_session(
        "post",
        200,
        {"id": "msg-123", "folder": "outbox"},
    )
    resp = client.post(
        "/api/send",
        json={"invoice": _VALID_INVOICE, "recipient": "0208:be0674415660"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["response"]["id"] == "msg-123"


def test_send_aborts_on_fatal_rules(client: FlaskClient) -> None:
    resp = client.post("/api/send", json={"invoice": {}, "recipient": "0208:be0674415660"})
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["error"] == "Validation failed"
    assert any(r["type"] == "FATAL" for r in data["rules"])


def test_send_missing_recipient(client: FlaskClient) -> None:
    resp = client.post("/api/send", json={"invoice": _VALID_INVOICE})
    assert resp.status_code == 400
    assert "recipient" in resp.get_json()["error"]


def test_send_missing_credentials(client_no_creds: FlaskClient) -> None:
    resp = client_no_creds.post(
        "/api/send",
        json={"invoice": _VALID_INVOICE, "recipient": "0208:be0674415660"},
    )
    assert resp.status_code == 500
