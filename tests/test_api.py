"""Tests for peppol_sender.api — message packaging and API client."""

import base64
from unittest.mock import MagicMock, patch

from peppol_sender.api import (
    get_org_info,
    get_report,
    lookup_participant,
    package_message,
    search_business_card,
    send_message,
)

SAMPLE_XML = b"<Invoice>test</Invoice>"


def test_package_message_structure() -> None:
    msg = package_message(SAMPLE_XML, "9925:sender", "9908:recipient", "proc-type", "doc-type")
    assert msg["sender"] == "9925:sender"
    assert msg["recipient"] == "9908:recipient"
    assert msg["processType"] == "proc-type"
    assert msg["documentType"] == "doc-type"
    assert "fileContent" in msg


def test_package_message_base64_roundtrip() -> None:
    msg = package_message(SAMPLE_XML, "s", "r", "p", "d")
    decoded = base64.b64decode(msg["fileContent"])
    assert decoded == SAMPLE_XML


def test_package_message_all_keys_present() -> None:
    msg = package_message(SAMPLE_XML, "s", "r", "p", "d")
    assert set(msg.keys()) == {"sender", "recipient", "processType", "documentType", "fileContent"}


@patch("peppol_sender.api._session")
def test_send_message_success(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "abc-123"}
    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = send_message({"test": "body"}, "api-key-123")
    assert result["status_code"] == 200
    assert result["json"] == {"id": "abc-123"}

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs.kwargs["headers"]["X-Api-Key"] == "api-key-123"
    assert call_kwargs.kwargs["json"] == {"test": "body"}


@patch("peppol_sender.api._session")
def test_send_message_non_json_response(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.side_effect = ValueError("No JSON")
    mock_resp.text = "Internal Server Error"
    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = send_message({"test": "body"}, "api-key-123")
    assert result["status_code"] == 500
    assert result["json"] == {"error_text": "Internal Server Error"}


@patch("peppol_sender.api._session")
def test_send_message_custom_base_url(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    send_message({"test": "body"}, "key", base_url="https://custom.api.com/v2/")
    actual_url = mock_session.post.call_args[0][0]
    assert actual_url == "https://custom.api.com/v2/message"


@patch("peppol_sender.api._session")
def test_no_retry_on_client_error(mock_session_fn: MagicMock) -> None:
    """4xx responses should be returned immediately without retry."""
    mock_resp = MagicMock()
    mock_resp.status_code = 422
    mock_resp.json.return_value = {"error": "Unprocessable Entity"}
    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = send_message({"test": "body"}, "key")
    assert result["status_code"] == 422
    mock_session.post.assert_called_once()


@patch("peppol_sender.api._session")
def test_get_report_success(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"validationRules": [], "transmissionRules": ""}
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = get_report("msg-123", "api-key")
    assert result["status_code"] == 200
    assert result["json"]["validationRules"] == []

    actual_url = mock_session.get.call_args[0][0]
    assert actual_url.endswith("/message/msg-123/report")


@patch("peppol_sender.api._session")
def test_get_org_info(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "POCITO", "VAT": "BE0674415660"}
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = get_org_info("api-key")
    assert result["status_code"] == 200
    assert result["json"]["name"] == "POCITO"
    actual_url = mock_session.get.call_args[0][0]
    assert actual_url.endswith("/organization/info")


@patch("peppol_sender.api._session")
def test_lookup_participant(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"participantId": "0208:be0123456789"}
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = lookup_participant("0123456789", "BE", "api-key")
    assert result["status_code"] == 200
    assert result["json"]["participantId"] == "0208:be0123456789"
    call_kwargs = mock_session.get.call_args
    assert call_kwargs.kwargs["params"]["vatNumber"] == "0123456789"
    assert call_kwargs.kwargs["params"]["countryCode"] == "BE"


@patch("peppol_sender.api._session")
def test_search_business_card(mock_session_fn: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"entities": [{"name": [{"name": "POCITO"}], "countryCode": "BE"}]},
    ]
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_fn.return_value = mock_session

    result = search_business_card("0208:be0674415660", "api-key")
    assert result["status_code"] == 200
    assert result["json"][0]["entities"][0]["countryCode"] == "BE"
    call_kwargs = mock_session.get.call_args
    assert call_kwargs.kwargs["params"]["participantId"] == "0208:be0674415660"


def test_session_has_retry_adapter() -> None:
    """Verify _session() configures retry on the session."""
    from requests.adapters import HTTPAdapter

    from peppol_sender.api import _session

    session = _session()
    adapter = session.get_adapter("https://example.com")
    assert isinstance(adapter, HTTPAdapter)
    assert adapter.max_retries.total == 3  # type: ignore[union-attr]
    assert 503 in adapter.max_retries.status_forcelist  # type: ignore[union-attr]
