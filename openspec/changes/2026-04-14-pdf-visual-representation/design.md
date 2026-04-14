## Context

PEPPOL transmits UBL XML end-to-end; there is no companion PDF channel. Verified by inspection of `docs/openapi_peppyrus.json` — no `pdf`, `attachment`, or `EmbeddedDocument` references. The UBL standard provides a single well-defined place for a visual representation: `cac:AdditionalDocumentReference` with an `EmbeddedDocumentBinaryObject` carrying base64-encoded PDF bytes plus `mimeCode` and `filename` attributes.

BIS Billing 3.0 rule `PEPPOL-EN16931-R008` permits PDF, image, CSV, XLSX, ODS, and OOXML MIME types. Only one visual representation per invoice is expected. Receivers' accountancy software reads the embedded document and surfaces it to human users alongside the parsed structured data.

Today the tool produces no PDF at all. Users who want a PDF are stuck printing the webapp form or writing one by hand in a separate tool — and nothing ships with the PEPPOL transmission.

## Goals / Non-Goals

**Goals:**

- Produce a clean PDF from the same invoice JSON that feeds the UBL generator (single source of truth).
- Embed the PDF as exactly one `cac:AdditionalDocumentReference` per invoice.
- CLI `create` embeds by default; `--no-pdf` is an explicit opt-out.
- Webapp `Preview PDF` button shows the user what the receiver will see before they hit Send.
- Reuse the webapp's editorial aesthetic (Fraunces / Spectral / JetBrains Mono) in the PDF template so the two experiences feel like one product.

**Non-Goals:**

- Multiple attachments per invoice (R008 expects one visual; keep the API simple).
- Non-PDF attachments (CSV, XLSX, etc.) — can be added later if a real use case emerges.
- Accepting a user-supplied external PDF. Splits the source of truth; the PDF content could drift from the XML. Defer until there's evidence users want it.
- Custom branding (logo upload, colour themes, user stationery). Out of scope for the first cut; the default template is deliberately minimal.
- Internationalisation / multi-currency prettification in the PDF beyond what's already in the JSON.
- Server-side caching of rendered PDFs.

## Decisions

**Render from HTML + CSS via WeasyPrint**

- Single source of truth: the same JSON dict feeds both the UBL XML generator and the PDF renderer, guaranteeing the two can never disagree on line totals, party names, or bank details.
- HTML/CSS layout is far more maintainable than a reportlab flowable DSL. Editing an invoice field is an HTML tweak, not a coordinate calculation.
- WeasyPrint output quality is typographically clean and suitable for production invoices.
- Reuses the webapp's existing Jinja patterns.
- **Alternative**: `reportlab` — rejected, harder to maintain, uglier defaults.
- **Alternative**: `fpdf2` — pure Python with no system deps, but output quality is too low for customer-facing invoices.
- **Alternative**: user-supplied uploaded PDF — rejected as the default flow because the PDF content could drift from the XML. Could be added later as an escape hatch.

**System dependencies acknowledged**

- WeasyPrint needs Pango 1.44+, Cairo, and libgdk-pixbuf at the OS level. On Ubuntu/Debian: `apt install libpango-1.0-0 libpangoft2-1.0-0`. On macOS: `brew install pango cairo gdk-pixbuf`.
- Documented in README install section. If the import fails at startup, the webapp surfaces a clear error rather than crashing on first render.

**Template lives under `peppol_sender/templates/`, not `webapp/templates/`**

- The CLI needs to render PDFs too, so the template cannot live in the webapp directory. Keeping it adjacent to the library makes `pdf.py` self-contained.
- Fonts are loaded from `webapp/static/fonts/` (existing bundled Fraunces / Spectral / JetBrains Mono) via absolute paths. The webapp directory becomes a runtime asset dependency for both the library and the webapp — acceptable given they ship together.

**Default to embedding in the CLI**

- `cli.py create` embeds unless `--no-pdf` is passed. This matches user expectations (a sent invoice carries a PDF).
- The webapp always embeds on `/api/send`. No user-facing toggle — a sent invoice always has a PDF.
- Non-default behaviour is available via the CLI flag for users who intentionally want XML-only output (testing, debugging, or custom visual-representation flows).

**UBL sequence position**

- `cac:AdditionalDocumentReference` appears in the Invoice `xs:sequence` between `BuyerReference` and the party references (`AccountingSupplierParty` etc.). The UBL builder inserts it there; the helper is called from `_build_document` right after `BuyerReference`.

**Embedded binary object attributes**

- `mimeCode="application/pdf"`, `filename="<invoice_number>.pdf"`. The `<invoice_number>` fallback is the same default the rest of the generator uses (`INV-0001`).
- `cbc:DocumentDescription` is set to `"Commercial Invoice"` for invoices; can be widened when credit notes land.

**PDF size**

- Base64 inflates by ~33%. A typical WeasyPrint invoice runs 30–80 KB, so a base64-encoded blob is ~100 KB — well under any reasonable access-point message limit.
- No local size cap is imposed. If Peppyrus rejects oversize messages, the error surfaces from `send_message()`.

**New `pdf-rendering` capability**

- PDF generation is a genuinely new concern with its own module and template — it deserves its own spec rather than being buried inside `ubl-generation`. The UBL spec only covers the embedding mechanism.

## Risks / Trade-offs

- **Install tax**: WeasyPrint's system-lib footprint is the biggest downside. Mitigation: clear README instructions + a friendly error if the import fails.
- **Template drift**: future UBL fields added to the JSON may not appear in the PDF unless the template is updated. Mitigation: a test that renders a full invoice and extracts text, checking that key fields (invoice number, seller, total) are present.
- **Concurrency with other changes**: this change touches `peppol_sender/ubl.py` alongside the proposed credit-note and payment-means changes. The `_add_additional_document_reference()` helper and the post-`BuyerReference` insertion point are independent of those — no structural conflicts; whichever lands first, the others rebase cleanly.
- **Webapp preview performance**: each preview click re-renders the PDF. WeasyPrint takes ~200–500 ms for a one-page invoice; acceptable for a preview button. Caching is explicitly a non-goal for this change.
