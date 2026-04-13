"""Flask webapp for the Peppol invoice sender.

Single-page form for creating, validating and sending PEPPOL invoices.
Reuses the `peppol_sender` package as a library; localStorage in the
browser persists customer/template/defaults state.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Allow `python webapp/app.py` from the project root by ensuring the project
# root is on sys.path before importing peppol_sender.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from flask import Flask, jsonify, render_template, request  # noqa: E402

from peppol_sender.api import (  # noqa: E402
    get_org_info,
    lookup_participant,
    package_message,
    search_business_card,
    send_message,
)
from peppol_sender.ubl import generate_ubl  # noqa: E402
from peppol_sender.validator import validate_basic, validate_xsd  # noqa: E402

load_dotenv()

_DEFAULT_BASE_URL = "https://api.test.peppyrus.be/v1"
_PROCESS_TYPE = "cenbii-procid-ubl::urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
_DOCUMENT_TYPE = (
    "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    "::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1"
)

app = Flask(__name__)


def _creds() -> tuple[str, str, str] | None:
    """Read Peppyrus credentials from env. Returns None if API key is missing."""
    api_key = os.getenv("PEPPYRUS_API_KEY")
    sender_id = os.getenv("PEPPOL_SENDER_ID", "")
    base_url = os.getenv("PEPPYRUS_BASE_URL", _DEFAULT_BASE_URL)
    if not api_key:
        return None
    return api_key, sender_id, base_url


def _missing_credentials_response() -> tuple[Any, int]:
    return jsonify({"error": "Missing PEPPYRUS_API_KEY in environment"}), 500


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/org-info")
def api_org_info() -> tuple[Any, int]:
    creds = _creds()
    if creds is None:
        return _missing_credentials_response()
    api_key, _, base_url = creds
    resp = get_org_info(api_key, base_url)
    return jsonify(resp["json"]), resp["status_code"]


@app.route("/api/lookup")
def api_lookup() -> tuple[Any, int]:
    creds = _creds()
    if creds is None:
        return _missing_credentials_response()
    api_key, _, base_url = creds
    vat_number = request.args.get("vatNumber", "")
    country_code = request.args.get("countryCode", "")
    if not vat_number or not country_code:
        return jsonify({"error": "vatNumber and countryCode are required"}), 400
    resp = lookup_participant(vat_number, country_code, api_key, base_url)
    return jsonify(resp["json"]), resp["status_code"]


@app.route("/api/business-card")
def api_business_card() -> tuple[Any, int]:
    creds = _creds()
    if creds is None:
        return _missing_credentials_response()
    api_key, _, base_url = creds
    participant_id = request.args.get("participantId", "")
    if not participant_id:
        return jsonify({"error": "participantId is required"}), 400
    resp = search_business_card(participant_id, api_key, base_url)
    return jsonify(resp["json"]), resp["status_code"]


def _validate_invoice(invoice: dict[str, Any]) -> tuple[bytes, list[dict]]:
    xml = generate_ubl(invoice)
    rules = validate_basic(xml) + validate_xsd(xml)
    return xml, rules


@app.route("/api/validate", methods=["POST"])
def api_validate() -> tuple[Any, int]:
    invoice = request.get_json(silent=True) or {}
    _, rules = _validate_invoice(invoice)
    return jsonify({"rules": rules}), 200


@app.route("/api/send", methods=["POST"])
def api_send() -> tuple[Any, int]:
    creds = _creds()
    if creds is None:
        return _missing_credentials_response()
    api_key, sender_id, base_url = creds
    if not sender_id:
        return jsonify({"error": "Missing PEPPOL_SENDER_ID in environment"}), 500

    body = request.get_json(silent=True) or {}
    invoice = body.get("invoice", {})
    recipient = body.get("recipient", "")
    if not recipient:
        return jsonify({"error": "recipient is required"}), 400

    xml, rules = _validate_invoice(invoice)
    fatal = [r for r in rules if r["type"] == "FATAL"]
    if fatal:
        return jsonify({"rules": rules, "error": "Validation failed"}), 422

    message = package_message(xml, sender_id, recipient, _PROCESS_TYPE, _DOCUMENT_TYPE)
    resp = send_message(message, api_key, base_url)
    return jsonify({"rules": rules, "response": resp["json"]}), resp["status_code"]


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
