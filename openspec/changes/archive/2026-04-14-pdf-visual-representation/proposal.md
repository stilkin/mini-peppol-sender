## Why

PEPPOL has no separate PDF channel: `docs/openapi_peppyrus.json` contains zero references to `pdf`, `attachment`, or `EmbeddedDocument` (verified by grep). The only way to ship a human-readable representation alongside the structured UBL data is to **embed** the PDF inside the UBL XML itself via `cac:AdditionalDocumentReference/Attachment/EmbeddedDocumentBinaryObject`. PEPPOL BIS Billing 3.0 explicitly allows exactly one such visual representation per invoice (rule `PEPPOL-EN16931-R008` restricts allowed MIME types to PDF, image, CSV, XLSX, ODS, OOXML).

Receivers' accountancy software commonly surfaces this embedded PDF to end users alongside the parsed structured fields. Invoices without one give recipients only raw structured data — functional but unloved. Small-business recipients, in particular, expect a PDF.

## What Changes

- Add a new module `peppol_sender/pdf.py` exposing `render_pdf(invoice: dict) -> bytes`, using Jinja2 to render `peppol_sender/templates/invoice.html` and WeasyPrint to convert the HTML to a PDF.
- Add a minimal but presentable HTML template at `peppol_sender/templates/invoice.html` with header, seller/buyer, line items, totals, and payment means sections.
- Extend the UBL generator (`peppol_sender/ubl.py`) to optionally embed a rendered PDF as `cac:AdditionalDocumentReference/Attachment/EmbeddedDocumentBinaryObject`, positioned between `BuyerReference` and `AccountingSupplierParty` per the UBL `xs:sequence`.
- CLI: `create` embeds a PDF by default; add a `--no-pdf` flag to opt out.
- Webapp: add a `Preview PDF` button that POSTs the current form state to a new `/api/preview-pdf` route (returns `application/pdf`) and opens the result in a new tab. Embedding on `/api/send` is automatic.
- Add `weasyprint>=60` to runtime dependencies; document required system libs (Pango, Cairo, libgdk-pixbuf) in the README install section.

## Capabilities

### New Capabilities

- `pdf-rendering`: Render a human-readable PDF from the same invoice JSON that feeds the UBL generator, using Jinja2 + WeasyPrint.

### Modified Capabilities

- `ubl-generation`: Optionally embed a rendered PDF as a single `cac:AdditionalDocumentReference` per invoice.
- `webapp-ui`: New `Preview PDF` button.
- `webapp-api`: New `POST /api/preview-pdf` route.

## Impact

- New files: `peppol_sender/pdf.py`, `peppol_sender/templates/invoice.html`, `peppol_sender/templates/invoice.css` (or inline CSS in the template).
- `peppol_sender/ubl.py`: New `_add_additional_document_reference()` helper; optional `embed_pdf: bool` argument in the document builder (default `True`).
- `cli.py`: `--no-pdf` flag on `create`.
- `webapp/app.py`: `/api/preview-pdf` route.
- `webapp/templates/index.html`, `webapp/static/app.js`: Preview button + handler.
- `pyproject.toml`: `weasyprint>=60` runtime dep.
- `README.md`: Install prerequisites for WeasyPrint (system libs), PDF embedding section.
- `CLAUDE.md`: `--no-pdf` flag in the commands reference.
- `tests/test_pdf.py` (new), `tests/test_ubl.py`, `tests/test_cli.py`, `tests/test_webapp.py`: coverage for rendering, embedding, CLI flag, and preview route.
- **Not touched**: `peppol_sender/api.py`, `peppol_sender/validator.py`, `schemas/`.
