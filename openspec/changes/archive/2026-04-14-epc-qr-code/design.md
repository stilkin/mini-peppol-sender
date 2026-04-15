## Context

EPC QR Code (EPC069-12, "Quick Response Code: Guidelines to Enable the Data Capture for the Initiation of a SEPA Credit Transfer") is the SEPA-wide standard for encoding a payment pre-fill into a QR code. The payload is a plain UTF-8, line-delimited text string — no encryption, no signing, no proprietary encoding. Any QR encoder can produce one.

Current state: Peppify embeds a WeasyPrint-rendered PDF inside the UBL XML per BIS Billing 3.0 R008. The PDF's `.payment` block shows the IBAN, BIC, account holder, and invoice reference as text. A recipient pays by transcribing these into their banking app. Every major EU banking app supports scanning an EPC QR to pre-fill these fields automatically.

Adding the QR touches only the PDF render path. The UBL XML already carries the structured `cac:PaymentMeans` (IBAN, BIC, PaymentID) that the receiver's accounting software auto-reconciles with; the QR is strictly an on-PDF affordance for the human payer.

## Goals / Non-Goals

**Goals:**

- Render an EPC QR Code in the PDF's existing `.payment` block whenever the invoice carries a credit-transfer `payment_means` with a non-empty IBAN and a EUR currency.
- Encode exactly what a modern EU banking app expects per EPC069-12 version 002 (BIC optional).
- Use the invoice's existing reference (`payment_means.payment_id`, defaulting to `invoice_number`) as the **unstructured** remittance field — no ISO 11649 RF creditor reference in v1.
- Truncate the beneficiary name and/or the reference automatically when the combined payload would exceed the 331-byte EPC hard limit.
- Style the QR to match the invoice's editorial palette (warm brown on cream) rather than stark black/white.
- Use error correction **level Q (~25%)** so the QR is visually denser and more robust to print smudging than the spec's default level M.
- Stay within the prime directive: one small module, one new pure-Python dependency, no feature flags, no user toggles.

**Non-Goals:**

- Structured ISO 11649 RF creditor references with mod-97 check digits. Unstructured is fine and already interoperable with every bank app we care about.
- Logos in the center of the QR. Adds visual complexity, requires SVG compositing, and increases scanability risk — especially for banking apps, which use strict built-in scanners. Deferred indefinitely.
- Dot modules, rounded finder patterns, gradients, "qr-code-monkey"-style cosmetics. Same reason: banking-app scanners are conservative and these treatments are a scanability landmine.
- A user toggle (`embed_qr`) mirroring `embed_pdf`. The QR is always-on when eligible; there is no scenario where a Peppify user would want the PDF but not the QR.
- Non-EUR currencies. EPC069-12 version 002 is EUR-only. Silently skipping the QR for non-EUR invoices is simpler than refusing to render them.
- A separate PEPPOL/UBL element for the QR. The QR lives only in the PDF; the UBL XML is unchanged. Any receiver's software that wants structured payment data already has it in `cac:PaymentMeans`.
- Server-side caching or pre-rendering of QR codes.

## Decisions

**Library: `segno` (not `qrcode` + Pillow)**

- `segno` is pure Python, no C extensions, ~200 KB installed, actively maintained, outputs SVG natively.
- `qrcode` requires Pillow (~4 MB, C extensions) and rasterises to PNG; the SVG output from `segno` is vector, stays crisp at print DPI, and embeds cleanly inline into the Jinja template.
- The QR SVG for a typical Peppify payload at level Q is ~3-5 KB. No performance or size concerns.
- **Alternative rejected**: `qrcode[pil]` — adds a substantial binary dep and produces inferior output for our WeasyPrint pipeline.
- **Alternative rejected**: an external QR-as-a-service API — introduces a network call on every render, a vendor dependency, and a privacy concern (sends IBAN + amount to a third party). Unacceptable.

**Payload: EPC069-12 version 002, UTF-8, SCT, BIC-optional**

- Version `002` lets us omit the BIC field when the invoice doesn't carry one (most modern SEPA transfers derive BIC from IBAN).
- Charset `1` (UTF-8) — the only reasonable choice for European beneficiary names with diacritics.
- Identification `SCT` (SEPA Credit Transfer) — the only option for our use case.
- Purpose field left empty (4-char codes like `GDDS`/`CHAR` exist but most banking apps don't surface them, and omitting the field is spec-compliant).
- **Line 10 (structured reference) left empty**; **line 11 (unstructured remittance) carries the invoice reference**. Using both is forbidden by the spec.

**Error correction: level Q (~25%)**

- The EPC spec recommends level M (~15%) as default, but higher is allowed and is what Peppify will use.
- Level Q gives ~25% module redundancy, meaningfully more robust to print smudging, folding, coffee stains, and low-quality phone cameras.
- At our payload size (~100-150 bytes typical) the version bump from M to Q is one QR version tier — the physical size difference in the PDF is negligible (a few modules wider, still well under 30 mm square at our target print size).
- Level Q also leaves headroom if we ever add a small centered logo; no code change would be required to support it beyond the SVG compositing step.
- **Alternative considered**: level H (~30%) — unnecessary redundancy for a freshly-printed invoice; one more version tier of size inflation for marginal benefit.

**Truncation strategy for the 331-byte EPC hard limit**

- The combined payload has a hard ceiling of 331 bytes across all 12 fields. In practice the fields that blow this limit are the beneficiary name (max 70 chars per spec) and the unstructured remittance (max 140 chars per spec). The other fields are fixed-size or short.
- Strategy: build the payload with raw inputs first. If over 331 bytes: truncate the unstructured reference to fit. If still over: truncate the beneficiary name to fit. Emit the truncated payload.
- A warning on stderr (or a debug note in the view model) is out of scope — the truncation is silent. Real-world inputs very rarely come close to the limit; logging a warning that 99.99% of users will never see is ceremony.

**Gating rules (all must hold for the QR to render)**

1. `invoice.payment_means.iban` is non-empty.
2. `invoice.currency` is `"EUR"` (case-insensitive).
3. `payment_means.code` is absent, `"30"`, or `"58"` (credit-transfer codes per UNCL4461). Non-credit-transfer means code (cash, cheque, direct debit) skips the QR regardless of IBAN presence.

Any gate failing → `build_epc_payload()` returns `None` → view model's `epc_qr_svg` is `None` → template's `{% if epc_qr_svg %}` block is skipped. The rest of the payment section renders normally as today.

**Color theme: warm brown on cream**

- `dark="#4a2c1d"` (the same warm brown already used for `.section-label` and the `.payment` left border)
- `light="#f7f2e8"` (the `.payment` block's existing background cream)
- High contrast ratio (verified ≈9:1, well above WCAG AA), safe for banking-app scanners.
- Matches the invoice's editorial Fraunces/Spectral palette rather than breaking it with a stark black square.

**QR size and placement**

- Target print size ~28 mm × 28 mm, positioned to the right of the IBAN text inside the existing `.payment` block.
- `.payment` becomes a two-column flex layout: IBAN/BIC/account text on the left, QR + "Scan to pay" caption on the right.
- Plenty of quiet zone preserved by the SVG renderer (segno's `border` parameter; default is 4 modules which is exactly what ISO 18004 requires).

**Module location: `peppol_sender/epc_qr.py`**

- New module alongside `pdf.py` (which is its only caller).
- Two public functions: `build_epc_payload(invoice: dict) -> str | None` and `render_qr_svg(payload: str) -> str`. Keeping them separate lets tests exercise payload construction without invoking segno.
- Pure function, no I/O, no configuration — easy to unit-test.

## Risks / Trade-offs

- **Bank-app scanability variance**: not every EU banking app implements EPC QR identically. A small number of older apps (some private/regional banks, some pre-2022 releases) don't recognise version 002. Mitigation: our payload is a clean, spec-compliant v2 EPC string; if a specific app doesn't read it, that's the app's problem, not ours. Testing with one's own banking app is advised before shipping to production (same caveat as the rest of the PEPPOL pipeline).
- **Spec ambiguity around whitespace**: EPC069-12 is unclear about trailing whitespace and whether empty lines count toward the byte limit. We'll emit no trailing whitespace, use `\n` as the line delimiter, and include empty lines only where mandated by the field position (since fields are positional, not keyed). This matches the behaviour of existing reference implementations.
- **Truncation can produce less-informative references**: a 200-char reference gets cut to ~140. In practice Peppify references are invoice numbers (<20 chars), so truncation is a theoretical edge case.
- **Color contrast vs. pure-black convention**: some scanners thresholding on strict black/white may be marginally less happy with a warm-brown foreground than a pure-black one. The chosen colour has ≥9:1 contrast, well inside the safe zone for any compliant scanner. If a specific app surfaces an issue, the fallback is a one-line CSS / param change to `dark="#000"`.
- **Segno dependency maturity**: segno is a small, focused library by one maintainer. It's been around since 2016, actively maintained, widely used, and has no known CVEs. Lower ecosystem footprint than qrcode+Pillow, at the cost of a smaller maintainer community. Acceptable.
- **Future logo support**: deferred indefinitely (see Non-Goals), but the level-Q error correction means we've left headroom to add one later without regenerating any payloads — purely an SVG compositing change on the rendering side.
