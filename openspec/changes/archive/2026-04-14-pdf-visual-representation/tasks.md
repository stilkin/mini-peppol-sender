## 1. Dependencies and Setup

- [x] 1.1 Add `weasyprint>=60` and `Jinja2>=3` to `[project].dependencies` in `pyproject.toml`; run `uv lock`
- [x] 1.2 Document system prerequisites (Pango, Cairo, libgdk-pixbuf) in `README.md` install section with per-OS commands

## 2. PDF Rendering Module

- [x] 2.1 Create `peppol_sender/templates/invoice.html` (Jinja template) with sections: header metadata, seller / buyer blocks, line items table, totals, payment means, notes
- [x] 2.2 Create `peppol_sender/templates/invoice.css` (or inline in the HTML) matching the webapp's Fraunces / Spectral / JetBrains Mono aesthetic; use `@page` rules for A4 margins
- [x] 2.3 Create `peppol_sender/pdf.py` with `render_pdf(invoice: dict) -> bytes` — loads the template with Jinja2, renders the HTML, pipes it through WeasyPrint, returns bytes
- [x] 2.4 Add a friendly `ImportError` handler so missing system libs surface as a clear actionable message

## 3. UBL Embedding

- [x] 3.1 Add `_add_additional_document_reference(parent, pdf_bytes, document_id, description)` helper in `peppol_sender/ubl.py` that base64-encodes the PDF and emits `cac:AdditionalDocumentReference/cbc:ID`, `cbc:DocumentDescription`, and `cac:Attachment/cbc:EmbeddedDocumentBinaryObject` with `mimeCode="application/pdf"` and `filename="<id>.pdf"`
- [x] 3.2 Extend the document builder with an `embed_pdf: bool = True` parameter; when enabled, call `render_pdf()` and `_add_additional_document_reference()` right after `BuyerReference` and before the party blocks (correct UBL `xs:sequence` position)
- [x] 3.3 Ensure the PDF embed path is opt-out for callers (testing / debugging) but opt-in-by-default for real use

## 4. CLI

- [x] 4.1 Add `--no-pdf` flag to the `create` subcommand in `cli.py` (default behaviour embeds PDF)
- [x] 4.2 Thread the flag through to `generate_ubl()` / `generate_credit_note()` via the `embed_pdf` parameter

## 5. Webapp

- [x] 5.1 Add `POST /api/preview-pdf` route in `webapp/app.py` that accepts the same invoice JSON as `/api/validate` and returns `application/pdf` bytes from `render_pdf()`
- [x] 5.2 Add a `Preview PDF` button to the form in `webapp/templates/index.html`, placed near `Validate` / `Send`
- [x] 5.3 Add a click handler in `webapp/static/app.js` that POSTs the form state to `/api/preview-pdf` and opens the returned blob in a new tab
- [x] 5.4 Confirm `/api/send` routes through the PDF embed path automatically (no user-facing toggle)

## 6. Tests

- [x] 6.1 `tests/test_pdf.py`: `render_pdf()` returns non-empty bytes starting with `%PDF-`; rendered PDF text (extracted via `pypdf` or similar) contains invoice number, seller name, and total
- [x] 6.2 `tests/test_ubl.py`: embedded-PDF path produces exactly one `cac:AdditionalDocumentReference` with correct `mimeCode`, `filename`, and base64-decodable content
- [x] 6.3 `tests/test_ubl.py`: `embed_pdf=False` produces no `AdditionalDocumentReference` element
- [x] 6.4 `tests/test_cli.py`: `create` embeds by default; `create --no-pdf` does not
- [x] 6.5 `tests/test_webapp.py`: `POST /api/preview-pdf` returns `200` with `Content-Type: application/pdf` and non-empty body
- [x] 6.6 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80`

## 7. Docs

- [x] 7.1 `README.md`: install prerequisites (Pango / Cairo), PDF embedding section, `--no-pdf` flag note, webapp `Preview PDF` button
- [x] 7.2 `CLAUDE.md`: `--no-pdf` flag, `Preview PDF` button in commands table
- [x] 7.3 `docs/invoice-json-schema.md`: note that the same JSON drives PDF rendering and UBL generation
