"""Command-line interface for peppol_sender minimal workflow.

Commands:
  create --input invoice.json --out invoice.xml
  validate --file invoice.xml
  send --file invoice.xml --recipient RECIPIENT_ID

Environment variables (preferred via .env):
  PEPPYRUS_API_KEY, PEPPOL_SENDER_ID, PEPPYRUS_BASE_URL
"""

import argparse
import json
import os

from dotenv import load_dotenv

from peppol_sender.api import get_report, package_message, send_message
from peppol_sender.ubl import generate_ubl
from peppol_sender.validator import validate_basic, validate_xsd

load_dotenv()


def cmd_create(args: argparse.Namespace) -> None:
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    xml = generate_ubl(data)
    with open(args.out, "wb") as f:
        f.write(xml)
    print(f"Generated UBL invoice: {args.out}")


def cmd_validate(args: argparse.Namespace) -> None:
    with open(args.file, "rb") as f:
        xml = f.read()
    rules = validate_basic(xml) + validate_xsd(xml)
    if not rules:
        print("OK: validation passed (no rules)")
    else:
        print("Validation rules:")
        for r in rules:
            print(f" - {r['type']}: {r['id']} - {r['message']} @ {r['location']}")


def cmd_send(args: argparse.Namespace) -> None:
    api_key = os.getenv("PEPPYRUS_API_KEY")
    sender = os.getenv("PEPPOL_SENDER_ID")
    base_url = os.getenv("PEPPYRUS_BASE_URL", "https://api.test.peppyrus.be/v1")
    if not api_key or not sender:
        print("Missing PEPPYRUS_API_KEY or PEPPOL_SENDER_ID in environment")
        return

    with open(args.file, "rb") as f:
        xml = f.read()

    # optional quick validation
    rules = validate_basic(xml)
    fatal = [r for r in rules if r["type"] == "FATAL"]
    if fatal:
        print("Found FATAL validation rules — abort send:")
        for r in fatal:
            print(f" - {r['id']}: {r['message']}")
        return

    process_type = args.processType or "cenbii-procid-ubl::urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    document_type = (
        args.documentType
        or "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
        "::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1"
    )

    message = package_message(xml, sender, args.recipient, process_type, document_type)
    resp = send_message(message, api_key, base_url)
    print(f"HTTP {resp['status_code']}")
    print(resp["json"])


def cmd_report(args: argparse.Namespace) -> None:
    api_key = os.getenv("PEPPYRUS_API_KEY")
    base_url = os.getenv("PEPPYRUS_BASE_URL", "https://api.test.peppyrus.be/v1")
    if not api_key:
        print("Missing PEPPYRUS_API_KEY in environment")
        return

    resp = get_report(args.id, api_key, base_url)
    print(f"HTTP {resp['status_code']}")

    report = resp["json"]
    validation_rules = report.get("validationRules", [])
    transmission_rules = report.get("transmissionRules", "")

    if not validation_rules and not transmission_rules:
        print("No rules reported.")
        return

    if validation_rules:
        print("Validation rules:")
        for r in validation_rules:
            print(f" - {r['type']}: {r['id']} - {r['message']} @ {r['location']}")

    if transmission_rules:
        print(f"Transmission rules: {transmission_rules}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("create")
    c.add_argument("--input", default="sample_invoice.json")
    c.add_argument("--out", default="invoice.xml")
    c.set_defaults(func=cmd_create)

    v = sub.add_parser("validate")
    v.add_argument("--file", default="invoice.xml")
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("send")
    s.add_argument("--file", default="invoice.xml")
    s.add_argument("--recipient", required=True, help="Recipient participant ID (e.g., 9908:nl987654321)")
    s.add_argument("--processType", required=False)
    s.add_argument("--documentType", required=False)
    s.set_defaults(func=cmd_send)

    r = sub.add_parser("report")
    r.add_argument("--id", required=True, help="Message ID returned by send")
    r.set_defaults(func=cmd_report)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
