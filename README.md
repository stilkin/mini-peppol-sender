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

The `send` command runs validation first and refuses to transmit if any FATAL rules are triggered. API calls retry automatically on server errors (5xx) with exponential backoff.

**Check the report** for a sent message:

```bash
python cli.py report --id <MESSAGE_ID>
```

## Invoice JSON format

See `sample_invoice.json` for a complete example. The expected structure:

```json
{
  "invoice_number": "INV-2025-001",
  "issue_date": "2025-11-29",
  "due_date": "2025-12-29",
  "invoice_type_code": "380",
  "currency": "EUR",
  "payment_terms": "Net 30 days",
  "seller": {
    "name": "ACME Consulting",
    "registration_name": "ACME Consulting BV",
    "endpoint_id": "BE0123456789",
    "endpoint_scheme": "0208",
    "country": "BE",
    "street": "Main Street 1",
    "city": "Brussels",
    "postal_code": "1000"
  },
  "buyer": {
    "name": "Client Corp",
    "registration_name": "Client Corp BV",
    "endpoint_id": "NL987654321",
    "endpoint_scheme": "0208",
    "vat": "NL987654321B01",
    "country": "NL"
  },
  "lines": [
    {
      "id": "1",
      "description": "Consulting service",
      "quantity": 1,
      "unit": "EA",
      "unit_price": 1000.00,
      "tax_category": "E",
      "tax_percent": 0
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `invoice_number` | string | Invoice identifier |
| `issue_date` | string | ISO 8601 date (YYYY-MM-DD) |
| `due_date` | string | Payment due date (optional if `payment_terms` set) |
| `invoice_type_code` | string | UBL type code (default: `380` = commercial invoice) |
| `currency` | string | ISO 4217 currency code (e.g. `EUR`) |
| `payment_terms` | string | Free-text payment terms (optional) |
| `seller.name` | string | Seller/supplier party name |
| `seller.registration_name` | string | Legal registration name (defaults to `name`) |
| `seller.endpoint_id` | string | Electronic address (e.g. VAT number) |
| `seller.endpoint_scheme` | string | Endpoint scheme ID (default: `0208`) |
| `seller.country` | string | ISO 3166-1 alpha-2 country code |
| `seller.street` | string | Street address (optional) |
| `seller.city` | string | City (optional) |
| `seller.postal_code` | string | Postal code (optional) |
| `seller.vat` | string | VAT number (optional, omit for VAT-exempt) |
| `buyer.*` | | Same fields as seller |
| `lines[].id` | string | Line item identifier |
| `lines[].description` | string | Item description |
| `lines[].quantity` | number | Quantity |
| `lines[].unit` | string | Unit code (default: `EA`) |
| `lines[].unit_price` | number | Price per unit |
| `lines[].line_extension_amount` | number | Optional; defaults to `quantity * unit_price` |
| `lines[].tax_category` | string | VAT category: `S` (standard), `E` (exempt), `O` (not subject) |
| `lines[].tax_percent` | number | VAT rate (use `0` for exempt) |

## Project structure

```
cli.py                  CLI entry point (create, validate, send, report)
peppol_sender/
  ubl.py                EN-16931 compliant UBL 2.1 XML generation
  validator.py           Structural + XSD validation
  api.py                 Peppyrus API client with retry (send, report)
schemas/xsd/            Official UBL 2.1 XSD schemas (OASIS)
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

- No Schematron / EN-16931 business rule validation (only structural checks + XSD).
- Only Invoice document type supported (no credit notes).
- API retry is limited to 3 attempts on 5xx errors; no persistent retry queue.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
