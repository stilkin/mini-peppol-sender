"""EPC QR Code builder for SEPA credit-transfer pre-fill.

Builds an EPC069-12 version 002 payload (BCD / SEPA QR / Girocode) from an
invoice dict and renders it as an inline SVG QR code, themed to the invoice
palette. The QR ends up in the PDF's payment block so EU banking apps can
pre-fill IBAN, beneficiary, amount, and reference with a single scan.

The payload is eligible only when:
- payment_means.iban is present and non-empty
- invoice.currency is EUR (case-insensitive)
- payment_means.code is "30", "58", or absent (credit transfer; mirrors BR-50)

Ineligible invoices yield `None` from `build_epc_payload()` — callers skip
rendering silently. Non-EUR / non-credit-transfer invoices are not errors.
"""

import io
from decimal import Decimal

import segno

# Credit-transfer payment means codes (UNCL4461). Mirrors validator._CREDIT_TRANSFER_CODES
# (kept local to avoid a cross-module import for a two-entry set).
_CREDIT_TRANSFER_CODES = {"30", "58"}

# EPC069-12 hard limit on total payload size, UTF-8 encoded.
_EPC_MAX_BYTES = 331

# EPC v002 max field lengths (spec EPC069-12).
_MAX_NAME_LEN = 70
_MAX_REF_LEN = 140

# Color theme — matches .section-label and .payment block in invoice.html.
_QR_DARK = "#4a2c1d"
_QR_LIGHT = "#f7f2e8"


def build_epc_payload(invoice: dict, grand_total: Decimal) -> str | None:
    """Return an EPC069-12 v002 payload string, or None if the invoice is ineligible.

    Caller supplies `grand_total` as a Decimal so the EPC amount stays byte-identical
    to the PDF/XML totals — no re-computation of tax groups in this module.
    """
    pm = invoice.get("payment_means") or {}
    iban = "".join((pm.get("iban") or "").split())
    if not iban:
        return None
    if (invoice.get("currency") or "").upper() != "EUR":
        return None
    code = pm.get("code")
    if code is not None and str(code) not in _CREDIT_TRANSFER_CODES:
        return None

    bic = pm.get("bic") or ""
    name = pm.get("account_name") or invoice.get("seller", {}).get("name") or ""
    ref = str(pm.get("payment_id") or invoice.get("invoice_number") or "")

    # Spec caps per-field lengths; apply before the payload-level 331-byte guard.
    name = name[:_MAX_NAME_LEN]
    ref = ref[:_MAX_REF_LEN]

    amount = f"EUR{grand_total:.2f}"

    # EPC069-12 v002 positional field layout (11 fields, LF-separated, no trailing B2B line).
    # Fields 9 and 10 (Purpose, Structured creditor reference) stay empty — line 11 is
    # the unstructured remittance. Empty slots are required by the spec's positional
    # parsing; do not rstrip the payload.
    fields = ["BCD", "002", "1", "SCT", bic, name, iban, amount, "", "", ref]

    # Truncate-to-fit: shrink unstructured reference first, then beneficiary name.
    # Real inputs very rarely exceed the 331-byte cap; this is a safety net, not a
    # hot path. Silent per design — no warning log.
    while len("\n".join(fields).encode("utf-8")) > _EPC_MAX_BYTES and fields[10]:
        fields[10] = fields[10][:-1]
    while len("\n".join(fields).encode("utf-8")) > _EPC_MAX_BYTES and fields[5]:
        fields[5] = fields[5][:-1]

    payload = "\n".join(fields)
    if len(payload.encode("utf-8")) > _EPC_MAX_BYTES:
        # Pathological non-truncatable input (e.g. malformed IBAN/BIC pushing the
        # fixed fields alone over the cap). Spec guarantees ≤ 331 bytes, so bail.
        return None
    return payload


def render_qr_svg(payload: str) -> str:
    """Return an inline SVG string for the EPC payload, themed and CSS-sizable.

    Uses level-Q error correction (~25% redundancy) for robustness to print
    smudging and to leave headroom for an optional future logo overlay. Omits
    XML declaration, xmlns, and explicit width/height so the SVG embeds cleanly
    inside the Jinja template and is sized entirely by CSS (`viewBox` preserves
    aspect ratio).
    """
    qr = segno.make(payload, error="q")
    buf = io.BytesIO()
    qr.save(
        buf,
        kind="svg",
        dark=_QR_DARK,
        light=_QR_LIGHT,
        xmldecl=False,
        svgns=False,
        omitsize=True,
    )
    return buf.getvalue().decode("utf-8")
