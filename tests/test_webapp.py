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


# ---------- payment means / BR-50 ----------


_PAYMENT_MEANS_SAMPLE = {
    "code": "30",
    "iban": "BE68539007547034",
    "bic": "BBRUBEBB",
    "account_name": "Seller BV",
}


def test_validate_with_payment_means_passes(client: FlaskClient) -> None:
    invoice = {**_VALID_INVOICE, "payment_means": _PAYMENT_MEANS_SAMPLE}
    resp = client.post("/api/validate", json=invoice)
    assert resp.status_code == 200
    rules = resp.get_json()["rules"]
    assert not any(r["id"] == "LOCAL-BR-50" for r in rules)


def test_validate_with_partial_payment_means_triggers_br50(client: FlaskClient) -> None:
    invoice = {**_VALID_INVOICE, "payment_means": {"code": "30"}}
    resp = client.post("/api/validate", json=invoice)
    assert resp.status_code == 200
    rules = resp.get_json()["rules"]
    br50 = [r for r in rules if r["id"] == "LOCAL-BR-50"]
    assert len(br50) == 1
    assert br50[0]["type"] == "FATAL"


@patch("peppol_sender.api._session")
def test_send_routes_payment_means_through(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    mock_session_fn.return_value = _mock_session(
        "post",
        200,
        {"id": "msg-pm-001"},
    )
    invoice = {**_VALID_INVOICE, "payment_means": _PAYMENT_MEANS_SAMPLE}
    resp = client.post(
        "/api/send",
        json={"invoice": invoice, "recipient": "0208:be0674415660"},
    )
    assert resp.status_code == 200
    # The POST body sent to Peppyrus contains the base64-encoded XML; decode
    # and confirm the structured PayeeFinancialAccount/ID is present.
    import base64

    posted_kwargs = mock_session_fn.return_value.post.call_args.kwargs
    body = posted_kwargs["json"]
    xml = base64.b64decode(body["fileContent"]).decode("utf-8")
    assert "PayeeFinancialAccount" in xml
    assert "BE68539007547034" in xml
    assert "BBRUBEBB" in xml


# ---------- /api/preview-pdf ----------


def test_preview_pdf_returns_pdf(client: FlaskClient) -> None:
    resp = client.post("/api/preview-pdf", json=_VALID_INVOICE)
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF-")
    assert len(resp.data) > 1000


def test_preview_pdf_uses_invoice_number_as_filename(client: FlaskClient) -> None:
    resp = client.post("/api/preview-pdf", json=_VALID_INVOICE)
    assert resp.status_code == 200
    disposition = resp.headers.get("Content-Disposition", "")
    assert "INV-001.pdf" in disposition


@patch("peppol_sender.api._session")
def test_send_flow_embeds_pdf_in_xml(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    """/api/send routes through _validate_invoice with embed_pdf=True by default,
    so the sent XML must contain a cac:AdditionalDocumentReference block."""
    import base64

    mock_session_fn.return_value = _mock_session("post", 200, {"id": "msg-pdf-001"})
    resp = client.post(
        "/api/send",
        json={"invoice": _VALID_INVOICE, "recipient": "0208:be0674415660"},
    )
    assert resp.status_code == 200
    posted_kwargs = mock_session_fn.return_value.post.call_args.kwargs
    xml = base64.b64decode(posted_kwargs["json"]["fileContent"]).decode("utf-8")
    assert "AdditionalDocumentReference" in xml
    assert "application/pdf" in xml


@patch("peppol_sender.api._session")
def test_send_flow_skips_pdf_when_embed_pdf_false(mock_session_fn: MagicMock, client: FlaskClient) -> None:
    """?embed_pdf=false on /api/send skips PDF embedding."""
    import base64

    mock_session_fn.return_value = _mock_session("post", 200, {"id": "msg-no-pdf"})
    resp = client.post(
        "/api/send?embed_pdf=false",
        json={"invoice": _VALID_INVOICE, "recipient": "0208:be0674415660"},
    )
    assert resp.status_code == 200
    posted_kwargs = mock_session_fn.return_value.post.call_args.kwargs
    xml = base64.b64decode(posted_kwargs["json"]["fileContent"]).decode("utf-8")
    assert "AdditionalDocumentReference" not in xml


def test_validate_embed_pdf_false_omits_pdf(client: FlaskClient) -> None:
    """?embed_pdf=false on /api/validate skips PDF embedding — verified by the
    absence of side effects (no raising when WeasyPrint isn't exercised)."""
    # The validate route doesn't return the XML, so we assert it still returns
    # 200 with an empty rules list (i.e. the skipped-PDF path doesn't break
    # validation). This is a smoke check; the real observable is in /api/send.
    resp = client.post("/api/validate?embed_pdf=false", json=_VALID_INVOICE)
    assert resp.status_code == 200
    assert resp.get_json()["rules"] == []
