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
from peppol_sender.ubl import generate_ubl
from peppol_sender.validator import validate_basic
from peppol_sender.api import package_message, send_message
from dotenv import load_dotenv

load_dotenv()


def cmd_create(args):
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    xml = generate_ubl(data)
    with open(args.out, 'wb') as f:
        f.write(xml)
    print(f'Generated UBL invoice: {args.out}')


def cmd_validate(args):
    with open(args.file, 'rb') as f:
        xml = f.read()
    rules = validate_basic(xml)
    if not rules:
        print('OK: basic validation passed (no rules)')
    else:
        print('Validation rules:')
        for r in rules:
            print(f" - {r['type']}: {r['id']} - {r['message']} @ {r['location']}")


def cmd_send(args):
    api_key = os.getenv('PEPPYRUS_API_KEY')
    sender = os.getenv('PEPPOL_SENDER_ID')
    base_url = os.getenv('PEPPYRUS_BASE_URL', 'https://api.test.peppyrus.be/v1')
    if not api_key or not sender:
        print('Missing PEPPYRUS_API_KEY or PEPPOL_SENDER_ID in environment')
        return

    with open(args.file, 'rb') as f:
        xml = f.read()

    # optional quick validation
    rules = validate_basic(xml)
    fatal = [r for r in rules if r['type'] == 'FATAL']
    if fatal:
        print('Found FATAL validation rules — abort send:')
        for r in fatal:
            print(f" - {r['id']}: {r['message']}")
        return

    processType = args.processType or 'cenbii-procid-ubl::urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
    documentType = args.documentType or 'busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1'

    message = package_message(xml, sender, args.recipient, processType, documentType)
    resp = send_message(message, api_key, base_url)
    print(f"HTTP {resp['status_code']}")
    print(resp['json'])


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')

    c = sub.add_parser('create')
    c.add_argument('--input', default='sample_invoice.json')
    c.add_argument('--out', default='invoice.xml')
    c.set_defaults(func=cmd_create)

    v = sub.add_parser('validate')
    v.add_argument('--file', default='invoice.xml')
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser('send')
    s.add_argument('--file', default='invoice.xml')
    s.add_argument('--recipient', required=True, help='Recipient participant ID (e.g., 9908:nl987654321)')
    s.add_argument('--processType', required=False)
    s.add_argument('--documentType', required=False)
    s.set_defaults(func=cmd_send)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return
    args.func(args)


if __name__ == '__main__':
    main()
