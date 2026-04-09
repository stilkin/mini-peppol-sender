"""Tests for peppol_sender.api — message packaging and API client."""

import base64
from unittest.mock import MagicMock, patch

from peppol_sender.api import package_message, send_message

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


@patch("peppol_sender.api.requests.post")
def test_send_message_success(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "abc-123"}
    mock_post.return_value = mock_resp

    result = send_message({"test": "body"}, "api-key-123")
    assert result["status_code"] == 200
    assert result["json"] == {"id": "abc-123"}

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["X-Api-Key"] == "api-key-123"
    assert call_kwargs.kwargs["json"] == {"test": "body"}


@patch("peppol_sender.api.requests.post")
def test_send_message_non_json_response(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.side_effect = ValueError("No JSON")
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    result = send_message({"test": "body"}, "api-key-123")
    assert result["status_code"] == 500
    assert result["json"] == {"error_text": "Internal Server Error"}


@patch("peppol_sender.api.requests.post")
def test_send_message_custom_base_url(mock_post: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_post.return_value = mock_resp

    send_message({"test": "body"}, "key", base_url="https://custom.api.com/v2/")
    actual_url = mock_post.call_args[0][0]
    assert actual_url == "https://custom.api.com/v2/message"
