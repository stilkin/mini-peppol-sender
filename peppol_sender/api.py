"""Peppyrus API client helpers.

Provides functions to package a UBL invoice into the MessageBody JSON and
send it to the Peppyrus `/message` endpoint. Uses `requests` to perform HTTP
calls and expects `X-Api-Key` in headers.
"""

import base64
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _session() -> requests.Session:
    """Return a session with retry on transient server errors."""
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


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
    resp = _session().post(url, json=message_body, headers=headers, timeout=30)
    return _parse_response(resp)


def get_report(message_id: str, api_key: str, base_url: str = "https://api.test.peppyrus.be/v1") -> dict[str, Any]:
    """GET /message/{id}/report and return parsed JSON on success."""
    url = base_url.rstrip("/") + f"/message/{message_id}/report"
    headers = {"X-Api-Key": api_key}
    resp = _session().get(url, headers=headers, timeout=30)
    return _parse_response(resp)


def get_org_info(api_key: str, base_url: str = "https://api.test.peppyrus.be/v1") -> dict[str, Any]:
    """GET /organization/info — fetch the authenticated organization's details."""
    url = base_url.rstrip("/") + "/organization/info"
    resp = _session().get(url, headers={"X-Api-Key": api_key}, timeout=30)
    return _parse_response(resp)


def lookup_participant(
    vat_number: str,
    country_code: str,
    api_key: str,
    base_url: str = "https://api.test.peppyrus.be/v1",
) -> dict[str, Any]:
    """GET /peppol/bestMatch — find a PEPPOL participant by VAT number + country."""
    url = base_url.rstrip("/") + "/peppol/bestMatch"
    params = {"vatNumber": vat_number, "countryCode": country_code}
    resp = _session().get(url, headers={"X-Api-Key": api_key}, params=params, timeout=30)
    return _parse_response(resp)


def search_business_card(
    participant_id: str,
    api_key: str,
    base_url: str = "https://api.test.peppyrus.be/v1",
) -> dict[str, Any]:
    """GET /peppol/search?participantId=... — fetch the PEPPOL directory business card."""
    url = base_url.rstrip("/") + "/peppol/search"
    resp = _session().get(
        url,
        headers={"X-Api-Key": api_key},
        params={"participantId": participant_id},
        timeout=30,
    )
    return _parse_response(resp)
