# PDF Rendering

Renders a human-readable PDF of an invoice from the same JSON data structure that feeds the UBL generator. Used by the CLI (to embed in UBL), the webapp (for the `Preview PDF` button and for embed on send), and any future callers that need a visual representation. Backed by Jinja2 (`peppol_sender/templates/invoice.html`) + WeasyPrint, with a lazy WeasyPrint import so consumers that never call `render_pdf()` do not need Pango/Cairo installed at the OS level.

## ADDED Requirements

### Requirement: Render invoice PDF from JSON

The `render_pdf(invoice: dict) -> bytes` function MUST produce a PDF byte string from a valid invoice dict using a Jinja2 HTML template and WeasyPrint. The WeasyPrint import MUST be lazy (inside the function body) so that importing `peppol_sender.pdf` does not require the WeasyPrint system libraries.

#### Scenario: Valid invoice renders a non-empty PDF

- **WHEN** `render_pdf()` is called with a complete invoice dict (seller, buyer, at least one line, totals)
- **THEN** it returns bytes starting with the `%PDF-` header and at least a few kilobytes long

#### Scenario: Template source

- **WHEN** `render_pdf()` is called
- **THEN** it loads `peppol_sender/templates/invoice.html` via Jinja2 with the pre-computed view model as the rendering context, passes the rendered HTML through WeasyPrint, and returns the PDF bytes

#### Scenario: Minimal invoice still renders

- **WHEN** `render_pdf()` is called with an invoice that omits optional fields (no `due_date`, no `payment_means`, no `service_date` on lines)
- **THEN** the function still returns a valid PDF without raising

#### Scenario: Missing system libraries surface a clear error

- **WHEN** `render_pdf()` is invoked in an environment where WeasyPrint cannot load its system dependencies (Pango, Cairo, libgdk-pixbuf)
- **THEN** a `RuntimeError` is raised with an actionable message that names the missing libraries and points to the README install section — not a raw `ImportError` or low-level library stack trace

### Requirement: View model pre-computes all display values

The renderer MUST pre-compute a view model (all totals, per-line display values, formatted strings) in Python before handing off to the Jinja template. The template MUST remain logic-free beyond simple iteration and conditional blocks.

#### Scenario: Totals match the XML generator

- **WHEN** the view model is built from a given invoice dict
- **THEN** its `subtotal`, `tax_total`, and `grand_total` values equal the values that `generate_ubl()` would emit in `LegalMonetaryTotal/LineExtensionAmount`, `TaxTotal/TaxAmount`, and `LegalMonetaryTotal/PayableAmount` respectively, for the same input, including for mixed-rate invoices (same `(tax_category, tax_percent)` grouping and Decimal rounding)

#### Scenario: Line extension amount override

- **WHEN** a line item supplies an explicit `line_extension_amount` (e.g. for a discounted line)
- **THEN** the view model's `line_total` for that line uses the explicit value, not `quantity * unit_price`

#### Scenario: Payment means absent

- **WHEN** the invoice dict does not contain a `payment_means` key
- **THEN** the view model's `payment_means` field is `None` and the template omits the payment section entirely (no empty heading, no placeholder text)

### Requirement: PDF layout contains required sections

The rendered PDF MUST include the core invoice sections that a human reader expects: header metadata, seller and buyer parties, line items with per-line totals, a totals block, and a payment section when `payment_means` is set.

#### Scenario: All core sections render

- **WHEN** an invoice with all fields populated (including `payment_means`) is rendered
- **THEN** the PDF contains identifiable sections for invoice metadata (number, issue date, due date), a `From` seller block, a `Bill to` buyer block, a line items table with descriptions / quantities / unit prices / line totals, a totals block (subtotal, tax, grand total), and a payment section showing IBAN and BIC

#### Scenario: Payment section omitted when absent

- **WHEN** an invoice without a `payment_means` block is rendered
- **THEN** the payment section is omitted from the PDF (no empty heading, no placeholder text)

#### Scenario: Service date shown inline

- **WHEN** a line item has a `service_date`
- **THEN** the PDF shows the service date as a muted sublabel under the line description
