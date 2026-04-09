# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Peppol Sender is a minimal Python scaffold for generating UBL 2.1 invoices from JSON, validating them, and sending them to the Peppyrus Access Point API (PEPPOL-compliant e-invoicing service).

## Commands

```bash
# Setup
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt   # includes runtime + dev deps

# Copy and fill in environment variables
cp .env.example .env

# Generate UBL XML from invoice JSON
python cli.py create --input sample_invoice.json --out invoice.xml

# Validate an invoice XML
python cli.py validate --file invoice.xml

# Send invoice to Peppyrus API
python cli.py send --file invoice.xml --recipient <RECIPIENT_ID>

# Fetch validation/transmission report for a sent message
python cli.py report --id <MESSAGE_ID>

# Lint and format
ruff check .          # lint (add --fix for auto-fix)
ruff format .         # format

# Type checking
mypy .

# Tests
pytest                    # run all tests
pytest -k test_name       # run a single test by name
pytest tests/test_ubl.py  # run a single test file

# Pre-commit hooks (ruff + mypy, installed via `pre-commit install`)
pre-commit run --all-files
```

## Architecture

The project follows a functional pipeline: **JSON → UBL XML → Validation → API transmission**.

- **`cli.py`** — CLI entry point with subcommands: `create`, `validate`, `send`, `report`
- **`peppol_sender/ubl.py`** — `generate_ubl(invoice: dict) -> bytes` builds EN-16931 compliant UBL 2.1 XML with proper `cbc:`/`cac:` namespaces
- **`peppol_sender/validator.py`** — `validate_basic()` checks required EN-16931 elements; `validate_xsd()` validates against UBL 2.1 XSD schemas in `schemas/`
- **`peppol_sender/api.py`** — Peppyrus API client with retry (3 attempts, exponential backoff on 5xx): `package_message()`, `send_message()`, `get_report()`

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
- Development plan and roadmap: `docs/development_plan.md`
- Test endpoint: `https://api.test.peppyrus.be/v1`
