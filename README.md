# Peppol Sender

A minimal Python CLI **and web UI** for generating EN-16931 compliant UBL 2.1 invoices, validating them locally, and sending them to the [PEPPOL](https://peppol.org/) e-invoicing network via the [Peppyrus](https://peppyrus.be/) Access Point API.

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
| `PEPPOL_SENDER_ID` | Yes | Your PEPPOL participant ID (e.g. `0208:0674415660`) |
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

## Web UI

A single-page Flask web form is available for users who'd rather click than edit JSON:

```bash
python webapp/app.py
# open http://127.0.0.1:5000
```

What it does:

- **Seller auto-fill** — your company details are fetched from Peppyrus `/organization/info` on page load and shown on a read-only seller card.
- **Buyer lookup** — enter a VAT number and country code, click "Look up" and the app calls `/peppol/bestMatch` to resolve the participant ID, then `/peppol/search` to enrich with the company's directory name, country, and city (best effort).
- **Recent customers** — every successfully sent invoice stores the buyer for one-click reuse. Updates to an existing customer overwrite the previous entry (keyed on participant ID).
- **Line item cards** — each line has its own description row and a 6-column grid for quantity, unit, price, VAT category, %, and computed total. Totals recalculate live as you type. Units and VAT categories are strict dropdowns so they can never fail `BR-CL-23`.
- **Line templates** — click the ★ on any line to save it as a template. Load from the dropdown under the items section.
- **Settings ⚙** — a modal (top-right gear icon) stores your defaults in browser localStorage:
  - Currency, payment terms (multi-line), due-date offset, default tax category and percent
  - **Your contact info** (name, email, phone) — automatically added to every outgoing invoice as `cac:Contact`
- **Auto-incrementing invoice number** — the last number sent is persisted and the next one is pre-filled.
- **Validate before send** — the backend runs both structural and XSD validation; if any FATAL rules are returned, the send is blocked and the rules are shown inline.
- **Recipient auto-fill** — when you look up a buyer or pick a recent one, the "Send to participant" field is populated from the buyer's endpoint.

All persistent state lives in **browser localStorage** — no server-side database. Your Peppyrus API key stays in the Flask process and never leaves the server.

## Invoice JSON format

See `sample_invoice.json` for a complete example. The expected structure:

```json
{
  "invoice_number": "INV-2025-001",
  "issue_date": "2025-11-29",
  "due_date": "2025-12-20",
  "invoice_type_code": "380",
  "currency": "EUR",
  "payment_terms": "Net 21 days",
  "seller": {
    "name": "ACME Consulting",
    "registration_name": "ACME Consulting BV",
    "endpoint_id": "0123456789",
    "endpoint_scheme": "0208",
    "vat": "BE0123456789",
    "legal_id": "0123456789",
    "legal_id_scheme": "0208",
    "country": "BE",
    "street": "Main Street 1",
    "city": "Brussels",
    "postal_code": "1000",
    "contact_name": "Jane Doe",
    "contact_email": "jane@example.be",
    "contact_phone": "+32 14 00 00 00"
  },
  "buyer": {
    "name": "Client Corp",
    "registration_name": "Client Corp BV",
    "endpoint_id": "987654321",
    "endpoint_scheme": "0208",
    "vat": "NL987654321B01",
    "legal_id": "987654321",
    "country": "NL",
    "street": "Client Ave 42",
    "city": "Amsterdam",
    "postal_code": "1011"
  },
  "lines": [
    {
      "id": "1",
      "description": "Consulting service",
      "quantity": 1,
      "unit": "HUR",
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
| `issue_date` | string | ISO 8601 date (YYYY-MM-DD); defaults to today |
| `due_date` | string | Payment due date (optional) |
| `invoice_type_code` | string | UBL type code (default: `380` = commercial invoice) |
| `currency` | string | ISO 4217 currency code (e.g. `EUR`) |
| `payment_terms` | string | Free-text payment terms; multi-line supported |
| `seller.name` | string | Trading name |
| `seller.registration_name` | string | Legal registration name (defaults to `name`) |
| `seller.endpoint_id` | string | Electronic address (e.g. enterprise number, no country prefix) |
| `seller.endpoint_scheme` | string | Endpoint scheme ID (default: `0208` for Belgian CBE) |
| `seller.vat` | string | VAT identifier (BT-31), e.g. `BE0674415660` |
| `seller.legal_id` | string | Legal registration identifier (BT-30), usually the enterprise number |
| `seller.legal_id_scheme` | string | Optional scheme ID for `legal_id` (e.g. `0208` for Belgium) |
| `seller.country` | string | ISO 3166-1 alpha-2 country code (uppercase) |
| `seller.street` | string | Street address (optional) |
| `seller.city` | string | City (optional) |
| `seller.postal_code` | string | Postal code (optional) |
| `seller.contact_name` | string | Contact person name (BT-41, optional) |
| `seller.contact_email` | string | Contact email (BT-43, optional) |
| `seller.contact_phone` | string | Contact phone (BT-42, optional) |
| `buyer.*` | | Same fields as seller (BT-44..63) |
| `lines[].id` | string | Line item identifier |
| `lines[].description` | string | Item description |
| `lines[].quantity` | number | Quantity |
| `lines[].unit` | string | UN/CEFACT Rec. 20 unit code (default: `EA`) — e.g. `HUR`, `DAY`, `KGM`, `LTR` |
| `lines[].unit_price` | number | Price per unit |
| `lines[].line_extension_amount` | number | Optional; defaults to `quantity * unit_price` |
| `lines[].tax_category` | string | VAT category: `S` (standard), `E` (exempt), `O` (not subject), `Z`, `AE`, `K`, `G`, `L`, `M` |
| `lines[].tax_percent` | number | VAT rate (use `0` for exempt) |

## Project structure

```
cli.py                     CLI entry point (create, validate, send, report)
peppol_sender/
  ubl.py                   EN-16931 compliant UBL 2.1 XML generation
  validator.py             Structural + XSD validation (cached schema)
  api.py                   Peppyrus API client with retry
webapp/
  app.py                   Flask app and routes
  templates/index.html     Single-page invoice form
  static/                  CSS + vanilla JS (localStorage-backed state)
tests/                     pytest suite (unit + Flask test client)
schemas/xsd/               Official UBL 2.1 XSD schemas (OASIS)
docs/
  openapi_peppyrus.json    Peppyrus OpenAPI 3.0 specification
  development_plan.md      Architecture and roadmap notes
openspec/                  Spec-driven change history (archived)
```

## Development

```bash
ruff check .                     # lint
ruff format .                    # format
mypy .                           # type check
pytest                           # run the test suite
pytest -k test_name              # run a single test by name
pytest tests/test_ubl.py         # run a single test file
pre-commit run --all-files       # run all pre-commit hooks
```

Coverage is enforced at ≥ 80% via `--cov-fail-under=80` in `pyproject.toml` (currently ~99%).

Pre-commit hooks (Ruff + MyPy) are installed via `pre-commit install`.

## Limitations

- No Schematron / EN-16931 business rule validation (only structural checks + XSD).
- Only Invoice document type supported (no credit notes).
- API retry is limited to 3 attempts on 5xx errors; no persistent retry queue.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
