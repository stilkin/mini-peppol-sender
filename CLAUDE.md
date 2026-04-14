# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Peppify is a minimal Python scaffold for generating UBL 2.1 invoices from JSON, validating them, and sending them to the Peppyrus Access Point API (PEPPOL-compliant e-invoicing service).

## Commands

Dependencies are managed with `uv` (declared in `pyproject.toml`, pinned in
`uv.lock`). Prefix every command with `uv run` or activate the venv first
(`. .venv/bin/activate`).

```bash
# Setup
uv sync                               # creates .venv, installs runtime + dev deps

# Copy and fill in environment variables
cp .env.example .env

# Generate UBL XML from invoice JSON (embeds a rendered PDF by default)
uv run python cli.py create --input sample_invoice.json --out invoice.xml

# XML-only output (skip the embedded PDF)
uv run python cli.py create --input sample_invoice.json --out invoice.xml --no-pdf

# Validate an invoice XML
uv run python cli.py validate --file invoice.xml

# Send invoice to Peppyrus API
uv run python cli.py send --file invoice.xml --recipient <RECIPIENT_ID>

# Fetch validation/transmission report for a sent message
uv run python cli.py report --id <MESSAGE_ID>

# Run the web UI (http://127.0.0.1:5000)
uv run python webapp/app.py

# Lint and format
uv run ruff check .          # lint (add --fix for auto-fix)
uv run ruff format .         # format

# Type checking
uv run mypy .

# Tests
uv run pytest                    # run all tests
uv run pytest -k test_name       # run a single test by name
uv run pytest tests/test_ubl.py  # run a single test file

# Pre-commit hooks (ruff + mypy, installed via `uv run pre-commit install`)
uv run pre-commit run --all-files
```

## Architecture

The project follows a functional pipeline: **JSON → UBL XML → Validation → API transmission**.

- **`cli.py`** — CLI entry point with subcommands: `create`, `validate`, `send`, `report`
- **`peppol_sender/ubl.py`** — `generate_ubl(invoice: dict, *, embed_pdf: bool = False) -> bytes` builds EN-16931 compliant UBL 2.1 XML with proper `cbc:`/`cac:` namespaces. When `embed_pdf=True`, renders a PDF via `peppol_sender.pdf` and embeds it as a `cac:AdditionalDocumentReference` (PEPPOL BIS Billing 3.0 R008 visual representation). Library default is `False` so the existing test suite stays fast and byte-stable; CLI `create` and webapp `/api/validate`+`/api/send` pass `embed_pdf=True` explicitly.
- **`peppol_sender/pdf.py`** — `render_pdf(invoice: dict) -> bytes` renders a human-readable PDF using Jinja2 (`peppol_sender/templates/invoice.html`) + WeasyPrint. `_build_view_model()` pre-computes all display values (totals use the same tax-group Decimal rounding as `ubl.py` so the PDF and XML totals are byte-identical). WeasyPrint is lazy-imported so Pango/Cairo are only required at render time.
- **`peppol_sender/validator.py`** — `validate_basic()` checks required EN-16931 elements and applies local BR-50 (IBAN required for credit transfer) and LOCAL-F001 (date format) rules; `validate_xsd()` validates against UBL 2.1 XSD schemas in `schemas/`
- **`peppol_sender/api.py`** — Peppyrus API client. Idempotent GET helpers retry transient 5xx failures (3 attempts, exponential backoff via `urllib3.Retry`); `send_message()` POSTs are intentionally **not** retried to avoid duplicate PEPPOL transmissions (POST is not in `urllib3`'s default `allowed_methods`). Functions: `package_message()`, `send_message()`, `get_report()`, `get_org_info()`, `lookup_participant()`, `search_business_card()`
- **`webapp/`** — Flask single-page invoice form. `app.py` exposes `/`, `/api/org-info`, `/api/lookup`, `/api/business-card`, `/api/validate`, `/api/send`, `/api/preview-pdf`. Templates in `templates/`, vanilla JS + CSS in `static/`. State (recent customers, line templates, defaults, last invoice number, seller bank account, seller contact, embed-PDF preference) lives in browser localStorage. The PEPPOL recipient is derived at send time from the buyer's `endpoint_scheme` + `endpoint_id` — there is no separate `#recipient` input in the form.

## Key Design Decisions

- Each module exports a single main function; no classes or complex abstractions
- UBL generator uses `cbc:`/`cac:` namespaces with strict element ordering (XSD `xs:sequence`)
- Tax calculation groups line items by `(tax_category, tax_percent)`; supports VAT-exempt (E/O)
- `validate_basic()` checks 11 mandatory EN-16931 elements: `CustomizationID`, `ProfileID`, `ID`, `IssueDate`, `InvoiceTypeCode`, `DocumentCurrencyCode`, `AccountingSupplierParty`, `AccountingCustomerParty`, `TaxTotal`, `LegalMonetaryTotal`, `InvoiceLine`
- Validation returns structured rule dicts with `id`, `type` (FATAL/WARNING), `location`, `message`
- CLI refuses to send if any FATAL validation rules are triggered
- Invoice XML is base64-encoded inside JSON for API transmission
- Configuration via `.env` files (PEPPYRUS_API_KEY, PEPPOL_SENDER_ID, PEPPYRUS_BASE_URL)

## Reference

- Peppyrus OpenAPI spec: `docs/openapi_peppyrus.json`
- Invoice JSON schema reference: `docs/invoice-json-schema.md`
- Test endpoint: `https://api.test.peppyrus.be/v1`
