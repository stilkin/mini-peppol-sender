"""Peppyrus API client helpers.

Provides functions to package a UBL invoice into the MessageBody JSON and
send it to the Peppyrus `/message` endpoint. Uses `requests` to perform HTTP
calls and expects `X-Api-Key` in headers.
"""

import base64
from typing import Any

import requests


def _parse_response(resp: requests.Response) -> dict[str, Any]:
    """Extract status code and parsed JSON (or error text) from a response."""
    result: dict[str, Any] = {"status_code": resp.status_code}
    try:
        result["json"] = resp.json()
    except ValueError:
        result["json"] = {"error_text": resp.text}
    return result


def package_message(
    xml_bytes: bytes,
    sender: str,
    recipient: str,
    process_type: str,
    document_type: str,
) -> dict[str, Any]:
    """Return MessageBody JSON ready to POST to Peppyrus.

    xml_bytes: raw bytes of the invoice XML (UTF-8)
    sender, recipient: participant IDs like '9925:be0123456789'
    process_type, document_type: strings from Peppol spec
    """
    b64 = base64.b64encode(xml_bytes).decode("ascii")
    return {
        "sender": sender,
        "recipient": recipient,
        "processType": process_type,
        "documentType": document_type,
        "fileContent": b64,
    }


def send_message(
    message_body: dict[str, Any],
    api_key: str,
    base_url: str = "https://api.test.peppyrus.be/v1",
) -> dict[str, Any]:
    """POST MessageBody to Peppyrus and return parsed JSON response."""
    url = base_url.rstrip("/") + "/message"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    resp = requests.post(url, json=message_body, headers=headers, timeout=30)
    return _parse_response(resp)


def get_report(message_id: str, api_key: str, base_url: str = "https://api.test.peppyrus.be/v1") -> dict[str, Any]:
    """GET /message/{id}/report and return parsed JSON on success."""
    url = base_url.rstrip("/") + f"/message/{message_id}/report"
    headers = {"X-Api-Key": api_key}
    resp = requests.get(url, headers=headers, timeout=30)
    return _parse_response(resp)
