# PDF Rendering

Renders a human-readable PDF of an invoice from the same JSON data structure that feeds the UBL generator. Used by the CLI (to embed in UBL), the webapp (for preview and for embed on send), and any future callers that need a visual representation.

## ADDED Requirements

### Requirement: Render invoice PDF from JSON

The `render_pdf(invoice: dict) -> bytes` function MUST produce a PDF byte string from a valid invoice dict using a Jinja2 HTML template and WeasyPrint.

#### Scenario: Valid invoice renders a non-empty PDF

- **WHEN** `render_pdf()` is called with a complete invoice dict (seller, buyer, at least one line, totals)
- **THEN** it returns bytes starting with the `%PDF-` header and at least a few kilobytes long

#### Scenario: PDF reflects invoice content

- **WHEN** an invoice with a specific invoice number, seller name, buyer name, and payable total is rendered
- **THEN** all of those values are present in the extracted text of the resulting PDF

#### Scenario: Template source

- **WHEN** `render_pdf()` is called
- **THEN** it loads `peppol_sender/templates/invoice.html` via Jinja2 with the invoice dict as the rendering context, passes the HTML through WeasyPrint, and returns the PDF bytes

#### Scenario: Missing system libraries surface a clear error

- **WHEN** `render_pdf()` is invoked in an environment where WeasyPrint cannot load its system dependencies (Pango, Cairo, libgdk-pixbuf)
- **THEN** a clear actionable error message is raised naming the missing libraries and pointing to the README install section — not a raw `ImportError` or low-level library stack trace

### Requirement: PDF layout contains required sections

The rendered PDF MUST include the core invoice sections that a human reader expects: header metadata, seller and buyer parties, line items, totals, and payment means (when present).

#### Scenario: All core sections render

- **WHEN** an invoice with all fields populated (including `payment_means`) is rendered
- **THEN** the PDF contains identifiable sections for invoice metadata (number, issue date, due date), a seller block, a buyer block, a line items table with descriptions / quantities / unit prices / line totals, a totals block (tax-exclusive, tax, tax-inclusive, payable), and a payment means block showing IBAN and BIC

#### Scenario: Payment means section omitted when absent

- **WHEN** an invoice without a `payment_means` block is rendered
- **THEN** the payment means section is omitted from the PDF (no empty heading, no placeholder text)
