## 1. Setup

- [ ] 1.1 Add `flask>=3.0` to `requirements.txt`
- [ ] 1.2 Create `webapp/` directory structure: `app.py`, `templates/`, `static/`

## 2. Flask Backend Routes

- [ ] 2.1 Create `webapp/app.py` with Flask app, load dotenv, configure `peppol_sender` imports
- [ ] 2.2 Add `GET /` route serving `index.html` template
- [ ] 2.3 Add `GET /api/org-info` route proxying Peppyrus `/organization/info`
- [ ] 2.4 Add `GET /api/lookup` route proxying Peppyrus `/peppol/bestMatch` (params: vatNumber, countryCode)
- [ ] 2.5 Add `GET /api/search` route proxying Peppyrus `/peppol/search` (params: name, country)
- [ ] 2.6 Add `POST /api/validate` route: accept invoice JSON, call `generate_ubl()` + `validate_basic()` + `validate_xsd()`, return rules
- [ ] 2.7 Add `POST /api/send` route: validate, then call `package_message()` + `send_message()`, return response

## 3. Invoice Form UI

- [ ] 3.1 Create `webapp/templates/index.html` with form structure: seller section (read-only), buyer section, line items table, invoice settings footer
- [ ] 3.2 Create `webapp/static/style.css` with clean form styling
- [ ] 3.3 Create `webapp/static/app.js` with core form logic: collect form data into invoice JSON, submit to backend
- [ ] 3.4 Add seller auto-population: fetch `/api/org-info` on page load, fill seller fields
- [ ] 3.5 Add buyer lookup: VAT input + "Lookup" button calling `/api/lookup`, fill buyer fields from response
- [ ] 3.6 Add dynamic line items: add/remove rows, auto-calculate line amounts and totals on input change
- [ ] 3.7 Add validate and send buttons: call `/api/validate` or `/api/send`, display results/errors in a status area

## 4. localStorage Features

- [ ] 4.1 Implement recent customers: save buyer after successful send, render dropdown on form load, pre-fill on select
- [ ] 4.2 Implement line item templates: save/load/select templates, render dropdown per line row
- [ ] 4.3 Implement invoice defaults: settings panel to edit currency, payment terms, due date offset, tax category/percent; apply on form load
- [ ] 4.4 Implement invoice number auto-increment: store last number after send, suggest next on form load

## 5. UI Polish

- [ ] 5.1 Use `frontend-design` skill to polish the HTML/CSS/JS for a clean, production-quality look

## 6. Docker

- [ ] 6.1 Create `Dockerfile` (python:3.12-slim, install requirements, copy project)
- [ ] 6.2 Create `docker-compose.yml` with `webapp` service (port 5000, env_file: .env)
- [ ] 6.3 Test `docker compose up webapp` serves the form and can send an invoice

## 7. Tests and Docs

- [ ] 7.1 Add `tests/test_webapp.py` with Flask test client: test each API route (org-info, lookup, validate, send with mocked Peppyrus)
- [ ] 7.2 Update CLAUDE.md with webapp commands (`python webapp/app.py`, Docker commands)
- [ ] 7.3 Update README with webapp section (quickstart, Docker, screenshots if applicable)
- [ ] 7.4 Run full suite, ensure all pass with `ruff`, `mypy`, coverage >= 80%
