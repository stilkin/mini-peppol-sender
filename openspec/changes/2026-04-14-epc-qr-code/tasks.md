## 1. Dependencies

- [x] 1.1 Add `segno>=1.6` to `[project].dependencies` in `pyproject.toml`; run `uv lock` and commit the lock change

## 2. EPC QR Module

- [x] 2.1 Create `peppol_sender/epc_qr.py` with two public functions: `build_epc_payload(invoice: dict) -> str | None` and `render_qr_svg(payload: str) -> str`
- [x] 2.2 `build_epc_payload()`: return `None` if `payment_means.iban` is missing/empty, if `invoice.currency` is not EUR (case-insensitive), or if `payment_means.code` is set to a non-credit-transfer code (anything outside `{"30", "58", None}`)
- [x] 2.3 `build_epc_payload()`: assemble the line-delimited EPC069-12 v002 payload with service tag `BCD`, version `002`, charset `1` (UTF-8), identification `SCT`, optional BIC, beneficiary name (defaulting to seller name if `payment_means.account_name` is absent), IBAN (whitespace-stripped), amount as `EUR<grand_total>` with 2 decimals, empty purpose, empty structured reference, unstructured remittance = `payment_means.payment_id` or `invoice_number`
- [x] 2.4 `build_epc_payload()`: if the UTF-8-encoded payload exceeds 331 bytes, truncate the unstructured reference first; if still too long, truncate the beneficiary name; re-check and return the truncated payload
- [x] 2.5 `render_qr_svg()`: call `segno.make(payload, error="q")` and return an inline SVG string with colors `dark="#4a2c1d"` / `light="#f7f2e8"`, no XML declaration (`xmldecl=False`), no namespace declaration (`svgns=False`), and no explicit width/height (`omitsize=True`) so CSS sizes it via the `viewBox`

## 3. PDF Rendering Integration

- [x] 3.1 Extend `peppol_sender/pdf.py`'s `_build_view_model()` to call `build_epc_payload(invoice, grand_total_dec)` and, on non-`None` payload, `render_qr_svg(payload)`; attach the result to the view model as `epc_qr_svg` (or `None`). Pass the pre-computed `Decimal` grand total to keep totals logic single-sourced
- [x] 3.2 Extend `peppol_sender/templates/invoice.html`: inside the existing `.payment` block, wrap the existing IBAN text in a left flex column (`payment-info`) and add a right flex column containing `{% if epc_qr_svg %}<div class="payment-qr">{{ epc_qr_svg | safe }}<div class="qr-hint">Scan with your banking app</div></div>{% endif %}`
- [x] 3.3 Add CSS rules for `.payment` (flex row, align-items start, gap 6mm), `.payment-info` (flex: 1), `.payment-qr` (fixed 28mm width, text-align center), `.payment-qr svg` (28mm × 28mm, display block), and `.qr-hint` (8pt italic in the muted grey already used for other hints)
- [x] 3.4 Confirm that the existing `.payment` block still renders correctly in the QR-absent path (non-EUR invoice, IBAN missing, non-credit-transfer code) — verified via `test_view_model_omits_epc_qr_for_non_eur_invoice` which asserts `class="payment-qr"` is NOT in the rendered HTML

## 4. Tests

- [x] 4.1 `tests/test_epc_qr.py`: `build_epc_payload()` returns a string with exactly 11 line-delimited fields (EPC069-12 v002 minimum, no trailing B2B line) for a typical EUR invoice
- [x] 4.2 `tests/test_epc_qr.py`: every field lands in the correct position — per-line content assertions for `SAMPLE_INVOICE` (`BCD`, `002`, `1`, `SCT`, `BBRUBEBB`, `ACME Consulting BV`, `BE68539007547034`, `EUR1000.00`, `""`, `""`, `INV-PDF-001`)
- [x] 4.3 `tests/test_epc_qr.py`: returns `None` when `payment_means.iban` is missing (covers both empty-string and missing-key cases)
- [x] 4.4 `tests/test_epc_qr.py`: returns `None` when `invoice.currency` is `USD`; accepts lowercase `eur`
- [x] 4.5 `tests/test_epc_qr.py`: returns `None` when `payment_means.code` is `"49"` (direct debit)
- [x] 4.6 `tests/test_epc_qr.py`: returns a valid payload when `payment_means.code` is `"30"`, `"58"`, or missing from the dict entirely
- [x] 4.7 `tests/test_epc_qr.py`: amount is formatted `EUR<grand_total>` with exactly 2 decimals, asserted byte-for-byte against a Decimal input
- [x] 4.8 `tests/test_epc_qr.py`: truncation — two tests, one for ASCII reference-only truncation, one for multibyte-emoji input that forces BOTH the reference loop AND the name loop to run (brings coverage to 100%)
- [x] 4.9 `tests/test_epc_qr.py`: `render_qr_svg()` returns a string starting with `<svg`, containing both `#4a2c1d` and `#f7f2e8`, with `viewBox=` and no `xmlns=`, and without explicit `width=`/`height=` on the root tag
- [x] 4.10 `tests/test_pdf.py`: a EUR credit-transfer invoice's view model has a non-None `epc_qr_svg` starting with `<svg`, and the rendered Jinja HTML contains `class="payment-qr"` and `Scan with your banking app`
- [x] 4.11 `tests/test_pdf.py`: a USD variant produces `epc_qr_svg is None` and the rendered HTML does NOT contain `class="payment-qr"` or `Scan with your banking app` (asserts the markup, not the CSS selector which always appears in the `<style>` block)
- [x] 4.12 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80` — all green, 129 passed, 99% coverage, `epc_qr.py` at 100%

## 5. Docs

- [x] 5.1 `README.md`: one sentence under "What it does" mentioning the EPC QR Code embedded in the PDF for EUR credit-transfer invoices
- [x] 5.2 `CLAUDE.md`: one-line entry in the Architecture section for `peppol_sender/epc_qr.py`, plus a note on `pdf.py`'s existing entry explaining how the QR is plumbed through the view model
