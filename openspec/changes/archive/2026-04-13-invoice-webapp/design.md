## Context

The CLI works end-to-end but requires editing JSON files. A web form would make the tool practical for day-to-day invoicing. The seller's own details are available from the Peppyrus API, and PEPPOL participant lookups can auto-fill buyer info. Browser localStorage provides persistence for customer history, templates, and defaults without needing a database.

## Goals / Non-Goals

**Goals:**
- Single-page invoice form that can validate and send invoices
- Minimise repetitive data entry through API lookups and localStorage
- Keep the API key server-side (never exposed to the browser)
- Docker setup for easy deployment

**Non-Goals:**
- User authentication / multi-tenant support
- Database-backed storage (localStorage is sufficient for a single-user tool)
- Invoice history / archive (Peppyrus tracks sent messages)
- PDF generation or print layouts

## Decisions

**Flask with Jinja2 templates + vanilla JS**
- Flask is lightweight and already planned in the dev plan. The seller auto-fill, buyer lookup, and dynamic line items need some JS, but a small amount of vanilla JS handles this without a build step or framework. HTMX is not needed for this scope.
- Alternative considered: FastAPI — rejected because we don't need async and Jinja2 templating is more natural in Flask.

**Project layout: `webapp/` subdirectory**
- `webapp/app.py` — Flask app with routes
- `webapp/templates/index.html` — single-page form template
- `webapp/static/` — CSS and JS files
- The webapp imports `peppol_sender` directly — no REST API layer between them.

**Flask routes**
- `GET /` — serve the invoice form
- `GET /api/org-info` — proxy to Peppyrus `/organization/info`
- `GET /api/lookup` — proxy to Peppyrus `/peppol/bestMatch` (params: vatNumber, countryCode)
- `GET /api/search` — proxy to Peppyrus `/peppol/search` (params: name, country)
- `POST /api/validate` — accept invoice JSON, generate UBL, run validation, return rules
- `POST /api/send` — validate + send, return response

**localStorage schema**
- `peppol_customers` — array of buyer objects (name, vat, address, participant_id)
- `peppol_line_templates` — array of line item templates (description, unit, unit_price, tax_category, tax_percent)
- `peppol_defaults` — object with currency, payment_terms, due_date_days, tax_category, tax_percent
- `peppol_last_invoice_number` — string of last used invoice number (auto-increment extracts trailing digits)

**Auto-increment invoice number**
- Parse trailing digits from last invoice number, increment, reconstruct. Example: `INV-2025-042` → `INV-2025-043`. If no trailing digits, append `-1`. Stored in localStorage after successful send.

**Docker: single image, compose for services**
- One `Dockerfile` based on `python:3.12-slim`, installs requirements, copies the project.
- `docker-compose.yml` defines one service `webapp` running `python webapp/app.py` on port 5000.
- Environment variables from `.env` passed via `env_file` in compose.
- The CLI is available inside the container for ad-hoc use.

**UI approach**
- Clean, functional form — not a design showcase, but polished enough for daily use.
- Use the `frontend-design` skill for the final HTML/CSS/JS to ensure good visual quality.
- Three form sections: Seller (auto-filled, collapsed), Buyer (lookup + recent dropdown), Line Items (dynamic table).
- Footer: invoice number, dates, payment terms, totals summary, Validate / Send buttons.
- Settings accessible via a collapsible panel or modal.

## Risks / Trade-offs

- **localStorage limits**: ~5-10 MB per origin. More than enough for customer lists and templates, but not suitable for storing invoice PDFs or large datasets.
- **Single-user assumption**: no auth, no multi-tenant. The API key in `.env` belongs to one organisation. This is fine for the stated use case.
- **No offline support**: the form needs the Flask backend running to validate and send. Lookups also need the backend. This is acceptable for a tool that sends invoices over the network anyway.
- **Flask dev server**: for a single-user tool, the Flask development server is adequate. For production deployment with multiple users, add gunicorn or similar. The Docker setup can be extended for this later.
