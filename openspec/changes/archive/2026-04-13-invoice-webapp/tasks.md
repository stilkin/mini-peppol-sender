## 1. Setup

- [x] 1.1 Add `flask>=3.0` to `requirements.txt`
- [x] 1.2 Create `webapp/` directory structure: `app.py`, `templates/`, `static/`

## 2. Flask Backend Routes

- [x] 2.1 Create `webapp/app.py` with Flask app, load dotenv, configure `peppol_sender` imports
- [x] 2.2 Add `GET /` route serving `index.html` template
- [x] 2.3 Add `GET /api/org-info` route proxying Peppyrus `/organization/info`
- [x] 2.4 Add `GET /api/lookup` route proxying Peppyrus `/peppol/bestMatch` (params: vatNumber, countryCode)
- [x] 2.5 Cache the UBL XSD schema in `validator.py` (`@functools.cache`) so webapp validate/send routes are fast
- [x] 2.6 Add `POST /api/validate` route: accept invoice JSON, call `generate_ubl()` + `validate_basic()` + `validate_xsd()`, return rules
- [x] 2.7 Add `POST /api/send` route: validate, then call `package_message()` + `send_message()`, return response
- [x] 2.8 Add `get_org_info()` and `lookup_participant()` helpers to `peppol_sender/api.py` (reuse `_session()` and `_parse_response()`)

## 3. Invoice Form UI

- [x] 3.1 Create `webapp/templates/index.html` with form structure: seller section (read-only), buyer section, line items table, invoice settings footer
- [x] 3.2 Create `webapp/static/style.css` with editorial paper aesthetic (Fraunces + Spectral + JetBrains Mono, oxblood accent, underline-only inputs)
- [x] 3.3 Create `webapp/static/app.js` with core form logic: collect form data into invoice JSON, submit to backend
- [x] 3.4 Add seller auto-population: fetch `/api/org-info` on page load, fill seller fields
- [x] 3.5 Add buyer lookup: VAT input + "Lookup" button calling `/api/lookup`, fill buyer fields from response
- [x] 3.6 Add dynamic line items: add/remove rows, auto-calculate line amounts and totals on input change
- [x] 3.7 Add validate and send buttons: call `/api/validate` or `/api/send`, display results/errors in a status area

## 4. localStorage Features

- [x] 4.1 Implement recent customers: save buyer after successful send, render dropdown on form load, pre-fill on select
- [x] 4.2 Implement line item templates: save/load/select templates, render dropdown per line row
- [x] 4.3 Implement invoice defaults: settings panel to edit currency, payment terms, due date offset, tax category/percent; apply on form load
- [x] 4.4 Implement invoice number auto-increment: store last number after send, suggest next on form load

## 5. UI Polish

- [x] 5.1 Use `frontend-design` skill to polish the HTML/CSS/JS for a clean, production-quality look

## 6. Docker (DEFERRED to follow-up change)

Docker setup is intentionally deferred so users can test the UI immediately. Will be addressed in a separate change.

## 7. Tests and Docs

- [x] 7.1 Add `tests/test_webapp.py` with Flask test client: test each API route (org-info, lookup, validate, send with mocked Peppyrus)
- [x] 7.2 Update CLAUDE.md with webapp commands (`python webapp/app.py`)
- [x] 7.3 Update README with webapp section
- [x] 7.4 Run full suite, ensure all pass with `ruff`, `mypy`, coverage >= 80%
