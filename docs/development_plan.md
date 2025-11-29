# Peppol Invoice Sender — Development Plan

Purpose
-------
This document describes a high-level implementation plan to build a small Python toolset that generates Peppol BIS Billing (UBL 2.1 / v3) invoices, validates them, and sends them over the Peppyrus Access Point API.

Scope & Goals
-------------
- Provide a minimal, maintainable Python package that can:
  - generate UBL 2.1 invoices from structured invoice data,
  - validate invoices (XSD + Schematron / EN-16931 business rules),
  - package and send invoices to Peppyrus using their `POST /message` API,
  - retrieve and interpret validation reports and transmission status.
- Provide a simple CLI to exercise the full flow and an optional minimal web form for manual entry.

Assumptions
-----------
- You have a Peppyrus `X-Api-Key` and a sender `participant ID` (iso6523 format). Test and prod keys will be handled via environment variables.
- The Peppyrus OpenAPI (provided) is the integration surface (test endpoint: `https://api.test.peppyrus.be/v1`).
- Invoice source: initially a single JSON template (manual entry / CLI). Later we can add CSV/DB import or a web form.

Milestones
----------
1. Project scaffold, packaging, and docs. (this file)
2. Implement core modules: UBL generator, validator, API client.
3. End-to-end CLI for create→validate→send→report on test endpoint.
4. Optional small Flask web form to create/send invoices interactively.
5. Tests, sample invoices, and deployment instructions.

High-level architecture
-----------------------
- `peppol_sender/ubl.py` — UBL generation (functional API: generate_ubl(invoice_data) -> bytes)
- `peppol_sender/validator.py` — Validation (xsd_validate(xml_bytes) and schematron_validate(xml_bytes) -> rules)
- `peppol_sender/api.py` — Peppyrus client: package_message(xml_bytes, sender, recipient, processType, documentType) and send_message(json_body, api_key, env)
- `cli.py` — Command line to run the workflow for a single invoice
- `webapp/app.py` (optional) — Flask app with a simple invoice entry form and Peppol lookup
- `tests/` — Unit tests and sample invoice fixtures

Data model
----------
- Use a simple JSON invoice structure for the generator input, e.g.:
  {
    "invoice_number": "INV-2025-001",
    "issue_date": "2025-11-29",
    "currency": "EUR",
    "seller": { "name": "My Co", "vat": "BE0123456789", "address": {...} },
    "buyer": { "name": "Client", "vat": "NL987654321", "address": {...}, "participant_id": "9908:nl987654321" },
    "lines": [ {"id": "1", "description": "Service", "quantity": 1, "unit": "EA", "unit_price": 100.00, "tax_percent": 21.0} ]
  }

Validation strategy
-------------------
- Structural validation: UBL 2.1 XSDs (ensure XML matches UBL schema). Use `lxml` or `xmlschema` in Python.
- Business-rule validation: EN-16931 Schematron rules (OpenPeppol BRs). Run Schematron with a processor (XSLT/Saxon) or use an online OpenPeppol validator where available.
- Local validation run before sending to reduce FATAL BR rejections.

API integration details
-----------------------
- Endpoint: `POST /message` on `https://api.test.peppyrus.be/v1` (switch to production URL when ready).
- Authentication: header `X-Api-Key: <key>`.
- Required JSON body (`MessageBody`): keys `sender`, `recipient`, `processType`, `documentType`, `fileContent` (base64 XML bytes).
- Example `processType` and `documentType` strings will be used from the OpenAPI spec (Peppol BIS Billing defaults).
- After send, poll `GET /message/{id}/report` to inspect `validationRules` and `transmissionRules`.

Error handling & retry policy
-----------------------------
- HTTP 401: fail early — invalid API key.
- HTTP 422: examine returned message — likely input formatting issue; fail and present error to user.
- Validation `FATAL` rules: treat as hard failure — do not retry; return to invoice generator for correction.
- Validation `WARNING` rules: log and optionally notify; allow acceptance.
- Network/5xx: implement retries with exponential backoff (e.g., 3 attempts with 1s, 3s, 10s delays).

Security & environment
----------------------
- API key and participant ID stored in environment variables or a safe secrets store: `PEPPYRUS_API_KEY`, `PEPPOL_SENDER_ID`.
- Use HTTPS for all requests.

Developer workflow (CLI)
------------------------
1. Prepare `invoice.json` (or use interactive prompt).  
2. `python cli.py create --input invoice.json` -> generates `invoice.xml` and runs validation.  
3. If validation passes (or only warnings), `cli.py send --file invoice.xml` will package and POST to the test endpoint.  
4. CLI prints Message `id` and a short summary of validation rules; user can `cli.py report --id <id>` to fetch full report.

Testing & QA
------------
- Unit tests for XML generation mapping (sample inputs -> expected XML fragments).  
- Integration tests that validate generated XML against UBL XSDs and Schematron rules.
- Manual end-to-end test against `https://api.test.peppyrus.be/v1` using the test `X-Api-Key`.

Deliverables (initial)
----------------------
- `peppol_sender` Python package with core modules.  
- `cli.py` demonstrating create→validate→send→report.  
- `docs/development_plan.md` (this file).  
- `README.md` with quickstart and environment variables.  

Next steps (recommendation)
--------------------------
1. I will scaffold the Python project and implement the minimal CLI and modules for the test flow (generate → validate → package → send).  
2. Provide two sample invoices (simple and multi-line) and unit tests.  
3. Add the optional web form if you want interactive entry and lookup integration.

Decision needed from you
------------------------
- Confirm you want me to scaffold the Python project now (I will implement the minimal packages and a `cli.py`).  
- Choose invoice input mode to scaffold: (A) single JSON template (recommended to start), (B) CSV/batch, or (C) web form only.

Date: 2025-11-29
