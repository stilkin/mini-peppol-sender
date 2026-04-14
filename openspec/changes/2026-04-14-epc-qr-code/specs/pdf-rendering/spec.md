# PDF Rendering

## MODIFIED Requirements

### Requirement: EPC QR Code in payment section

When an invoice is a EUR credit transfer and carries a non-empty IBAN, the rendered PDF's payment section MUST include an EPC QR Code (EPC069-12 version 002) encoding the payee's IBAN, beneficiary name, grand total, and invoice reference, so that a human payer can scan the code with an EU banking app to pre-fill the credit transfer.

Payload construction MUST be implemented in a dedicated module (`peppol_sender/epc_qr.py`) exposing a pure `build_epc_payload(invoice: dict) -> str | None` function and a `render_qr_svg(payload: str) -> str` function. The payload is a line-delimited UTF-8 string with service tag `BCD`, version `002`, charset `1`, identification `SCT`, optional BIC, beneficiary name, IBAN (whitespace-stripped), amount formatted as `EUR<grand_total>` with two decimals, empty purpose, empty structured reference, and the invoice reference as unstructured remittance. The QR code MUST be rendered with error correction **level Q** (~25% redundancy).

#### Scenario: EUR credit-transfer invoice shows a QR

- **WHEN** an invoice with `currency: "EUR"` and a `payment_means` block containing a non-empty `iban` is rendered
- **THEN** the rendered PDF's payment section contains an inline SVG QR code, positioned to the right of the IBAN text block, with the label `Scan to pay`

#### Scenario: Payload encodes the expected fields

- **WHEN** `build_epc_payload()` is called on an invoice with seller name `Acme BV`, IBAN `BE68539007547034`, BIC `GEBABEBB`, grand total `120.00`, and invoice number `INV-42`
- **THEN** the returned string's 12 line-delimited fields are `BCD`, `002`, `1`, `SCT`, `GEBABEBB`, `Acme BV`, `BE68539007547034`, `EUR120.00`, empty, empty, `INV-42`, empty

#### Scenario: Non-EUR invoice skips the QR silently

- **WHEN** an invoice with `currency: "USD"` (or any currency other than EUR) and a valid IBAN is rendered
- **THEN** `build_epc_payload()` returns `None`, the view model's `epc_qr_svg` is `None`, and the PDF renders successfully with the existing text-only payment section (no empty container, no error)

#### Scenario: Missing IBAN skips the QR silently

- **WHEN** an invoice has no `payment_means` block, or a `payment_means` block without an `iban` field, or with an empty `iban`
- **THEN** `build_epc_payload()` returns `None` and the PDF renders with no QR code

#### Scenario: Non-credit-transfer payment code skips the QR silently

- **WHEN** an invoice's `payment_means.code` is set to a value outside the credit-transfer set (anything other than `"30"`, `"58"`, or absent)
- **THEN** `build_epc_payload()` returns `None` regardless of IBAN presence

#### Scenario: Payload truncates to fit the 331-byte EPC limit

- **WHEN** the assembled payload would exceed 331 bytes (combined across all fields)
- **THEN** `build_epc_payload()` first truncates the unstructured remittance (invoice reference) to fit; if the payload is still too long, it then truncates the beneficiary name; the returned payload is guaranteed to be ≤ 331 bytes encoded as UTF-8

#### Scenario: BIC is optional per EPC v2

- **WHEN** an invoice's `payment_means` contains an IBAN but no BIC
- **THEN** `build_epc_payload()` emits an empty BIC field (the spec's line 5) and the QR is still produced; no banking app is expected to reject this because v002 makes BIC optional

#### Scenario: QR color theme matches invoice palette

- **WHEN** `render_qr_svg()` is called with a valid payload
- **THEN** the returned SVG uses foreground `#4a2c1d` (warm brown matching `.section-label`) and background `#f7f2e8` (matching the `.payment` block's cream fill), with contrast ≥ 9:1 (WCAG AA comfortable for scanners)

#### Scenario: QR uses level Q error correction

- **WHEN** `render_qr_svg()` generates the SVG
- **THEN** the underlying segno call uses `error="Q"` (~25% redundancy), making the QR resilient to light print degradation and leaving headroom for a future optional logo overlay without changing the payload
