"""Tests for peppol_sender.epc_qr — EPC QR payload builder and SVG renderer."""

from decimal import Decimal

from peppol_sender.epc_qr import build_epc_payload, render_qr_svg
from tests.test_pdf import SAMPLE_INVOICE


def test_payload_happy_path() -> None:
    payload = build_epc_payload(SAMPLE_INVOICE, Decimal("1000.00"))
    assert payload is not None
    fields = payload.split("\n")
    assert len(fields) == 11
    assert fields[0] == "BCD"
    assert fields[1] == "002"
    assert fields[2] == "1"
    assert fields[3] == "SCT"
    assert fields[4] == "BBRUBEBB"  # BIC
    assert fields[5] == "ACME Consulting BV"  # beneficiary name
    assert fields[6] == "BE68539007547034"  # IBAN
    assert fields[7] == "EUR1000.00"  # amount
    assert fields[8] == ""  # purpose (empty)
    assert fields[9] == ""  # structured creditor reference (empty)
    assert fields[10] == "INV-PDF-001"  # unstructured remittance = invoice number


def test_payload_skips_when_iban_missing() -> None:
    inv = {**SAMPLE_INVOICE, "payment_means": {"code": "30", "iban": ""}}
    assert build_epc_payload(inv, Decimal("1000.00")) is None


def test_payload_skips_when_payment_means_missing() -> None:
    inv = {k: v for k, v in SAMPLE_INVOICE.items() if k != "payment_means"}
    assert build_epc_payload(inv, Decimal("1000.00")) is None


def test_payload_skips_for_non_eur_currency() -> None:
    inv = {**SAMPLE_INVOICE, "currency": "USD"}
    assert build_epc_payload(inv, Decimal("1000.00")) is None


def test_payload_accepts_lowercase_eur() -> None:
    inv = {**SAMPLE_INVOICE, "currency": "eur"}
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None


def test_payload_skips_for_non_credit_transfer_code() -> None:
    inv = {**SAMPLE_INVOICE, "payment_means": {**SAMPLE_INVOICE["payment_means"], "code": "49"}}
    assert build_epc_payload(inv, Decimal("1000.00")) is None


def test_payload_accepts_credit_transfer_code_58() -> None:
    inv = {**SAMPLE_INVOICE, "payment_means": {**SAMPLE_INVOICE["payment_means"], "code": "58"}}
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None


def test_payload_accepts_missing_code_field() -> None:
    pm = {k: v for k, v in SAMPLE_INVOICE["payment_means"].items() if k != "code"}
    inv = {**SAMPLE_INVOICE, "payment_means": pm}
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None


def test_payload_defaults_name_to_seller_when_account_name_absent() -> None:
    pm = {k: v for k, v in SAMPLE_INVOICE["payment_means"].items() if k != "account_name"}
    inv = {**SAMPLE_INVOICE, "payment_means": pm}
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    fields = payload.split("\n")
    assert fields[5] == SAMPLE_INVOICE["seller"]["name"]


def test_payload_uses_payment_id_when_set() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "payment_means": {**SAMPLE_INVOICE["payment_means"], "payment_id": "CUSTOM-REF"},
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    assert payload.split("\n")[10] == "CUSTOM-REF"


def test_payload_strips_whitespace_from_iban() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "payment_means": {**SAMPLE_INVOICE["payment_means"], "iban": "BE68 5390 0754 7034"},
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    assert payload.split("\n")[6] == "BE68539007547034"


def test_payload_amount_matches_grand_total_byte_for_byte() -> None:
    payload = build_epc_payload(SAMPLE_INVOICE, Decimal("1234.56"))
    assert payload is not None
    assert payload.split("\n")[7] == "EUR1234.56"


def test_payload_amount_stays_ascii_regardless_of_language() -> None:
    """Guardrail: EPC069-12 is an ASCII-locked spec. Even when the PDF is rendered
    in Dutch/French/German, the EPC QR payload amount must stay `EUR1234.56` —
    never `EUR1.234,56`."""
    for lang in ("en", "nl", "fr", "de"):
        inv = {**SAMPLE_INVOICE, "language": lang}
        payload = build_epc_payload(inv, Decimal("1234.56"))
        assert payload is not None
        assert payload.split("\n")[7] == "EUR1234.56", f"EPC amount corrupted for lang={lang}"


def test_payload_truncation_of_reference_only() -> None:
    # 200-char ASCII reference is under the global cap once reference is shrunk,
    # but name stays intact. Exercises the reference-truncation loop.
    long_ref = "R" * 200
    inv = {
        **SAMPLE_INVOICE,
        "invoice_number": long_ref,
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    fields = payload.split("\n")
    assert fields[5] == "ACME Consulting BV"  # name unchanged
    assert len(fields[10]) < len(long_ref)  # reference shrunk
    assert fields[10].startswith("R")  # but still a reference
    assert len(payload.encode("utf-8")) <= 331


def test_payload_truncation_of_both_reference_and_name() -> None:
    # Force BOTH loops to run: 70 × 4-byte emoji = 280 bytes of name (at the per-field
    # char cap) plus 140 × 4-byte emoji = 560 bytes of reference (also at the cap).
    # After the reference loop drains all ~560 ref bytes, constants + name alone
    # still exceed 331, so the name loop runs too.
    emoji_name = "😀" * 70  # 70 chars, 280 UTF-8 bytes
    emoji_ref = "🔥" * 140  # 140 chars, 560 UTF-8 bytes
    inv = {
        **SAMPLE_INVOICE,
        "invoice_number": emoji_ref,
        "payment_means": {
            **SAMPLE_INVOICE["payment_means"],
            "account_name": emoji_name,
        },
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    assert len(payload.encode("utf-8")) <= 331
    fields = payload.split("\n")
    # Both fields were truncated from their starting length
    assert len(fields[5]) < 70  # name shrunk
    assert len(fields[10]) < 140  # reference shrunk
    # What's left is still valid (prefix of the original)
    assert fields[5] == "" or fields[5].startswith("😀")
    assert fields[10] == "" or fields[10].startswith("🔥")


def test_payload_returns_none_when_non_truncatable_fields_exceed_limit() -> None:
    # Pathological input: an IBAN longer than the whole EPC byte budget.
    # Name and reference get drained by the truncation loops, but the
    # IBAN itself keeps the payload over 331 bytes, so build_epc_payload
    # MUST return None rather than emit an oversized payload.
    inv = {
        **SAMPLE_INVOICE,
        "payment_means": {
            **SAMPLE_INVOICE["payment_means"],
            "iban": "B" * 400,
        },
    }
    assert build_epc_payload(inv, Decimal("1000.00")) is None


def test_payload_truncation_shrinks_reference_before_name() -> None:
    # Long enough that truncation must happen, but short enough that the
    # reference can absorb it all (name stays intact).
    long_ref = "R" * 200
    inv = {
        **SAMPLE_INVOICE,
        "invoice_number": long_ref,
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    fields = payload.split("\n")
    assert fields[5] == "ACME Consulting BV"  # name unchanged
    assert len(fields[10]) < len(long_ref)  # reference shrunk
    assert fields[10].startswith("R")  # but still a reference
    assert len(payload.encode("utf-8")) <= 331


def test_payload_handles_multibyte_chars_in_name() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "payment_means": {**SAMPLE_INVOICE["payment_means"], "account_name": "Café Brüderlé"},
    }
    payload = build_epc_payload(inv, Decimal("1000.00"))
    assert payload is not None
    assert "Café Brüderlé" in payload
    assert len(payload.encode("utf-8")) <= 331


def test_render_qr_svg_returns_themed_svg() -> None:
    payload = "BCD\n002\n1\nSCT\n\nTest\nBE68539007547034\nEUR10.00\n\n\nref"
    svg = render_qr_svg(payload)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>\n") or svg.endswith("</svg>")
    assert "#4a2c1d" in svg  # dark (themed brown)
    assert "#f7f2e8" in svg  # light (themed cream)
    assert "viewBox=" in svg  # sizing hook for CSS
    assert "xmlns=" not in svg  # svgns=False, inline HTML5 SVG


def test_render_qr_svg_omits_width_height_so_css_can_size_it() -> None:
    payload = "BCD\n002\n1\nSCT\n\nTest\nBE68539007547034\nEUR10.00\n\n\nref"
    svg = render_qr_svg(payload)
    # The root <svg ...> tag must not carry explicit width/height attributes;
    # CSS sizing in the Jinja template is the single source of truth.
    root = svg.split(">", 1)[0]
    assert " width=" not in root
    assert " height=" not in root
