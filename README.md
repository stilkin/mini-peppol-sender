# Peppol Sender (minimal Python scaffold)

This repository contains a minimal Python scaffold to generate a UBL 2.1 invoice,
perform basic validation, and send it to the Peppyrus Access Point API (`/message`).

Quickstart
----------
1. Create a virtual environment and install dependencies:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in `PEPPYRUS_API_KEY` and `PEPPOL_SENDER_ID`.

3. Generate an invoice XML from the sample JSON:

```sh
python cli.py create --input sample_invoice.json --out invoice.xml
```

4. Validate the generated XML (basic structural checks):

```sh
python cli.py validate --file invoice.xml
```

5. Send the invoice (specify recipient participant ID):

```sh
python cli.py send --file invoice.xml --recipient 9908:nl987654321
```

Notes
-----
- This scaffold uses a minimal local validator; for production you should
  perform full XSD and Schematron validation against the official UBL and
  EN-16931 rules.
- The CLI defaults to the Peppyrus test endpoint (`https://api.test.peppyrus.be/v1`),
  but you can override `PEPPYRUS_BASE_URL` in `.env` for production.
