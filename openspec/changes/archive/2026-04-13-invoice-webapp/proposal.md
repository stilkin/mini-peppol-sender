## Why

The CLI is functional but requires manually editing JSON files to create invoices. A minimal web UI would make the tool accessible for day-to-day use — fill in a form, click send. Repeated data entry (seller info, frequent customers, common line items) should be minimised through API lookups and browser-side storage.

## What Changes

- Add Flask webapp in `webapp/` with a single-page invoice form
- **Seller auto-population**: fetch company details from Peppyrus `/organization/info` on page load, pre-fill seller fields (read-only by default)
- **Buyer lookup**: input VAT number or name, look up PEPPOL participant via `/peppol/bestMatch` and `/peppol/search`, verify recipient can receive invoices
- **Recent customers**: store previously used buyers in localStorage, show as a selectable dropdown
- **Line item templates**: save and reuse common line items (description, unit, price) from localStorage
- **Invoice defaults**: store and auto-fill currency, payment terms, due date offset, default tax category/percent in localStorage
- **Auto-increment invoice number**: track last used invoice number in localStorage, suggest the next one
- **Dynamic line items**: add/remove rows with auto-calculated totals (line amounts, tax, grand total)
- **Validate & Send**: validate the invoice (basic + XSD) before sending, display validation results, send via Peppyrus API with the API key kept server-side
- Add `flask` to `requirements.txt`
- (Deferred: Docker Compose setup will land in a follow-up change.)

## Capabilities

### New Capabilities

- `webapp-ui`: Single-page invoice form with auto-population, lookup, localStorage convenience features, validate and send
- `webapp-api`: Flask backend routes — serve form, proxy Peppyrus API lookups (org info, participant search), handle validate/send

### Modified Capabilities

_None_ (webapp imports `peppol_sender` as a library; no changes to existing modules)

## Impact

- New `webapp/` directory: `app.py` (Flask routes), `templates/` (HTML), `static/` (CSS/JS)
- `requirements.txt`: add `flask>=3.0`
- New `Dockerfile` and `docker-compose.yml` at project root
- No changes to `peppol_sender/`, `cli.py`, or existing tests
