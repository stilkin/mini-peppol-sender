## 1. Dependencies

- [ ] 1.1 Add `segno>=1.6` to `[project].dependencies` in `pyproject.toml`; run `uv lock` and commit the lock change

## 2. EPC QR Module

- [ ] 2.1 Create `peppol_sender/epc_qr.py` with two public functions: `build_epc_payload(invoice: dict) -> str | None` and `render_qr_svg(payload: str) -> str`
- [ ] 2.2 `build_epc_payload()`: return `None` if `payment_means.iban` is missing/empty, if `invoice.currency` is not EUR (case-insensitive), or if `payment_means.code` is set to a non-credit-transfer code (anything outside `{"30", "58", None}`)
- [ ] 2.3 `build_epc_payload()`: assemble the line-delimited EPC069-12 v002 payload with service tag `BCD`, version `002`, charset `1` (UTF-8), identification `SCT`, optional BIC, beneficiary name (defaulting to seller name if `payment_means.account_name` is absent), IBAN (whitespace-stripped), amount as `EUR<grand_total>` with 2 decimals, empty purpose, empty structured reference, unstructured remittance = `payment_means.payment_id` or `invoice_number`
- [ ] 2.4 `build_epc_payload()`: if the UTF-8-encoded payload exceeds 331 bytes, truncate the unstructured reference first; if still too long, truncate the beneficiary name; re-check and return the truncated payload
- [ ] 2.5 `render_qr_svg()`: call `segno.make(payload, error="Q")` and return an inline SVG string with colors `dark="#4a2c1d"` / `light="#f7f2e8"`, `scale=1`, no XML declaration, no namespace declaration, small quiet zone (segno default of 4 modules is correct)

## 3. PDF Rendering Integration

- [ ] 3.1 Extend `peppol_sender/pdf.py`'s `_build_view_model()` to call `build_epc_payload(invoice)` and, on non-`None` payload, `render_qr_svg(payload)`; attach the result to the view model as `epc_qr_svg` (or `None`)
- [ ] 3.2 Extend `peppol_sender/templates/invoice.html`: inside the existing `.payment` block, wrap the existing IBAN text in a left flex column and add a right flex column containing `{% if epc_qr_svg %}<div class="payment-qr">{{ epc_qr_svg | safe }}</div><p class="qr-hint">Scan to pay</p>{% endif %}`
- [ ] 3.3 Add CSS rules for `.payment` (flex row, align-items start), `.payment-body` (left column, flex: 1), `.payment-qr` (fixed ~28mm width, vertical-align top), and `.qr-hint` (micro-text under the QR in the muted grey already used for other hints)
- [ ] 3.4 Confirm that the existing `.payment` block still renders correctly in the QR-absent path (non-EUR invoice, IBAN missing, non-credit-transfer code) — the right column simply doesn't exist and the IBAN text occupies the full width

## 4. Tests

- [ ] 4.1 `tests/test_epc_qr.py`: `build_epc_payload()` returns a string with exactly 12 lines (or 12 fields with final trailing newline, matching spec) for a typical EUR invoice
- [ ] 4.2 `tests/test_epc_qr.py`: every field lands in the correct position — assert per-line content for a fixture invoice
- [ ] 4.3 `tests/test_epc_qr.py`: returns `None` when `payment_means.iban` is missing
- [ ] 4.4 `tests/test_epc_qr.py`: returns `None` when `invoice.currency` is `USD` (or any non-EUR)
- [ ] 4.5 `tests/test_epc_qr.py`: returns `None` when `payment_means.code` is `"49"` (direct debit) or any non-credit-transfer value
- [ ] 4.6 `tests/test_epc_qr.py`: returns a valid payload when `payment_means.code` is explicitly `"30"` or `"58"` or absent
- [ ] 4.7 `tests/test_epc_qr.py`: amount is formatted `EUR<grand_total>` with exactly 2 decimals, matching the PDF/XML total byte-for-byte
- [ ] 4.8 `tests/test_epc_qr.py`: truncation — a very long beneficiary name + reference still produces a payload ≤ 331 bytes
- [ ] 4.9 `tests/test_epc_qr.py`: `render_qr_svg()` returns a string starting with `<svg` and containing the configured dark/light colors
- [ ] 4.10 `tests/test_pdf.py`: extending the existing PDF test, a rendered PDF for an EUR credit-transfer invoice contains an SVG QR (check the HTML render step's output, not the raster PDF, for presence of `<svg` with `dark="#4a2c1d"`)
- [ ] 4.11 `tests/test_pdf.py`: a non-EUR invoice or IBAN-less invoice renders successfully with no QR
- [ ] 4.12 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80`

## 5. Docs

- [ ] 5.1 `README.md`: add one sentence under "What it does" mentioning the EPC QR Code embedded in the PDF for EUR credit-transfer invoices
- [ ] 5.2 `CLAUDE.md`: add a one-line entry in the Architecture section for `peppol_sender/epc_qr.py`
