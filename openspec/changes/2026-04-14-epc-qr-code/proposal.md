## Why

Small-business recipients who receive an invoice want to pay it without retyping five fields. The **EPC QR Code** (European Payments Council, spec EPC069-12, also known as SEPA QR / BCD / Girocode) is the SEPA-wide standard for embedding a credit-transfer pre-fill into a printed or screen-rendered invoice: the payer scans it with their banking app and the IBAN, beneficiary name, amount, and reference are filled in automatically. It is supported by every major EU banking app (Belfius, KBC, ING, Argenta, Rabobank, N26, etc.) and is already what the Peppyrus sample renderer ships.

Today a Peppify PDF shows the IBAN/BIC as text; the receiver has to transcribe it. Adding the QR is a small, localised change with a direct UX win and no impact on PEPPOL transmission (the QR is a visual element on the PDF, not a UBL field).

## What Changes

- Add a new module `peppol_sender/epc_qr.py` exposing `build_epc_payload(invoice: dict) -> str | None` and `render_qr_svg(payload: str) -> str`.
- Extend `peppol_sender/pdf.py`'s `_build_view_model()` to attach an `epc_qr_svg` entry to the view model when an EPC QR can be generated for the invoice; `None` otherwise.
- Extend `peppol_sender/templates/invoice.html` to render the QR inside the `.payment` block, to the right of the IBAN text, when `epc_qr_svg` is set.
- Add `segno>=1.6` to runtime dependencies (pure Python, no C extensions, SVG output native).
- Gate the QR on three conditions: `payment_means.iban` is present; `invoice.currency == "EUR"`; the assembled payload fits the 331-byte EPC limit (with automatic truncation of the beneficiary name and reference to make it fit).

No changes to the UBL generator, validator, webapp API, webapp UI, CLI, or any other capability. QR rendering is internal to the PDF pipeline and invisible to every caller that isn't looking at the rendered bytes.

## Capabilities

### Modified Capabilities

- `pdf-rendering`: When a valid EUR credit-transfer invoice is rendered, the PDF's payment section includes an EPC QR Code that encodes the payee's IBAN, beneficiary name, amount, and invoice reference per EPC069-12.

## Impact

- **New files**: `peppol_sender/epc_qr.py`, `tests/test_epc_qr.py`.
- `peppol_sender/pdf.py`: extend `_build_view_model()` to call `build_epc_payload()` + `render_qr_svg()` and attach `epc_qr_svg` to the view model (≤10 lines).
- `peppol_sender/templates/invoice.html`: one conditional block inside the existing `.payment` section rendering the inline SVG, plus a small CSS rule for positioning and the color theme.
- `pyproject.toml`: `segno>=1.6` in `[project].dependencies`.
- `uv.lock`: regenerated.
- `README.md`: one paragraph under "What it does" describing the QR.
- `CLAUDE.md`: single line in the Architecture section referencing `epc_qr.py`.
- **Not touched**: `peppol_sender/ubl.py`, `peppol_sender/validator.py`, `peppol_sender/api.py`, `webapp/`, `cli.py`, `schemas/`, any other OpenSpec capability.
