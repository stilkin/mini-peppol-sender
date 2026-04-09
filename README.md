# Peppol Sender

A minimal Python CLI for generating UBL 2.1 invoices, validating them, and sending them to the [PEPPOL](https://peppol.org/) e-invoicing network via the [Peppyrus](https://peppyrus.be/) Access Point API.

## Quickstart

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt       # runtime only
# or
pip install -r requirements-dev.txt   # includes linting, typing, pre-commit
cp .env.example .env                  # then fill in your credentials (see below)
```

## Configuration

Set these in `.env` (or export them in your shell):

| Variable | Required | Description |
|---|---|---|
| `PEPPYRUS_API_KEY` | Yes | Your Peppyrus API key |
| `PEPPOL_SENDER_ID` | Yes | Your PEPPOL participant ID (e.g. `9925:be0123456789`) |
| `PEPPYRUS_BASE_URL` | No | API base URL. Defaults to the test endpoint `https://api.test.peppyrus.be/v1` |

## Usage

**Generate** a UBL 2.1 invoice XML from a JSON file:

```bash
python cli.py create --input sample_invoice.json --out invoice.xml
```

**Validate** the generated XML (basic structural checks):

```bash
python cli.py validate --file invoice.xml
```

**Send** the invoice to a recipient on the PEPPOL network:

```bash
python cli.py send --file invoice.xml --recipient 9908:nl987654321
```

The `send` command runs validation first and refuses to transmit if any FATAL rules are triggered.

## Invoice JSON format

See `sample_invoice.json` for a complete example. The expected structure:

```json
{
  "invoice_number": "INV-2025-001",
  "issue_date": "2025-11-29",
  "currency": "EUR",
  "seller": {
    "name": "ACME Consulting"
  },
  "buyer": {
    "name": "Client Corp"
  },
  "lines": [
    {
      "id": "1",
      "description": "Consulting service",
      "quantity": 1,
      "unit": "EA",
      "unit_price": 1000.00
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `invoice_number` | string | Invoice identifier |
| `issue_date` | string | ISO 8601 date (YYYY-MM-DD) |
| `currency` | string | ISO 4217 currency code (e.g. `EUR`) |
| `seller.name` | string | Seller/supplier party name |
| `buyer.name` | string | Buyer/customer party name |
| `lines[].id` | string | Line item identifier |
| `lines[].description` | string | Item description |
| `lines[].quantity` | number | Quantity |
| `lines[].unit` | string | Unit code (default: `EA`) |
| `lines[].unit_price` | number | Price per unit |
| `lines[].line_extension_amount` | number | Optional; defaults to `quantity * unit_price` |

## Project structure

```
cli.py                  CLI entry point (create, validate, send)
peppol_sender/
  ubl.py                UBL 2.1 XML generation from invoice dicts
  validator.py           Basic structural validation of UBL XML
  api.py                 Peppyrus API client (send, report)
docs/
  openapi_peppyrus.json  Peppyrus OpenAPI 3.0 specification
  development_plan.md    Architecture and roadmap notes
```

## Development

```bash
ruff check .                     # lint
ruff format .                    # format
mypy .                           # type check
pre-commit run --all-files       # run all pre-commit hooks
```

Pre-commit hooks (Ruff + MyPy) are installed via `pre-commit install`.

## Limitations

- The validator only checks for required element presence -- it does **not** perform full XSD or Schematron validation against official UBL/EN-16931 rules.
- The UBL generator produces a minimal invoice. Fields like addresses, tax breakdowns, and payment terms are not yet mapped.
- The `get_report()` function exists in `api.py` but is not yet wired into the CLI.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
