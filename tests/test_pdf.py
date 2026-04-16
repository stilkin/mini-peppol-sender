"""Tests for peppol_sender.pdf — invoice PDF rendering and view model."""

from decimal import Decimal
from xml.etree import ElementTree as ET

from peppol_sender.pdf import _build_view_model, render_pdf
from peppol_sender.ubl import generate_ubl

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


def _parse_benelux(s: str) -> Decimal:
    """Parse a BeNeLux-formatted amount (`1.234,56`) back to Decimal for cross-checks
    against the ASCII-formatted totals emitted by the UBL XML generator."""
    return Decimal(s.replace(".", "").replace(",", "."))


SAMPLE_INVOICE: dict = {
    "invoice_number": "INV-PDF-001",
    "issue_date": "2026-04-14",
    "due_date": "2026-05-05",
    "currency": "EUR",
    "buyer_reference": "PO-42",
    "payment_terms": "Net 21 days",
    "payment_means": {
        "code": "30",
        "iban": "BE68539007547034",
        "bic": "BBRUBEBB",
        "account_name": "ACME Consulting BV",
    },
    "seller": {
        "name": "ACME Consulting",
        "registration_name": "ACME Consulting BV",
        "endpoint_id": "BE0123456789",
        "endpoint_scheme": "0208",
        "vat": "BE0123456789",
        "country": "BE",
        "street": "Main Street 1",
        "city": "Brussels",
        "postal_code": "1000",
    },
    "buyer": {
        "name": "Client Corp",
        "registration_name": "Client Corp BV",
        "endpoint_id": "NL987654321",
        "endpoint_scheme": "0208",
        "vat": "NL987654321B01",
        "country": "NL",
        "street": "Client Ave 42",
        "city": "Amsterdam",
        "postal_code": "1011",
    },
    "lines": [
        {
            "id": "1",
            "description": "Consulting service",
            "quantity": 10,
            "unit": "HUR",
            "unit_price": 100.0,
            "tax_category": "E",
            "tax_percent": 0,
            "service_date": "2026-04-10",
        }
    ],
}


# --- view model ---


def test_view_model_minimal_totals() -> None:
    vm = _build_view_model(SAMPLE_INVOICE)
    assert vm["subtotal"] == "1.000,00"
    assert vm["tax_total"] == "0,00"
    assert vm["grand_total"] == "1.000,00"
    assert vm["currency"] == "EUR"
    assert len(vm["lines"]) == 1
    assert vm["lines"][0]["line_total"] == "1.000,00"
    assert vm["lines"][0]["service_date"] == "2026-04-10"


def test_view_model_with_standard_vat() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 2, "unit_price": 50.0, "tax_category": "S", "tax_percent": 21}],
    }
    vm = _build_view_model(inv)
    # 2 * 50 = 100; 21% = 21.00; total 121.00
    assert vm["subtotal"] == "100,00"
    assert vm["tax_total"] == "21,00"
    assert vm["grand_total"] == "121,00"


def test_view_model_mixed_rates() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "S", "tax_percent": 21},
            {"id": "2", "quantity": 1, "unit_price": 200.0, "tax_category": "S", "tax_percent": 6},
        ],
    }
    vm = _build_view_model(inv)
    # Group 1: 100 * 21% = 21.00
    # Group 2: 200 * 6%  = 12.00
    # Subtotal 300, tax 33, grand 333
    assert vm["subtotal"] == "300,00"
    assert vm["tax_total"] == "33,00"
    assert vm["grand_total"] == "333,00"


def test_view_model_totals_match_ubl_xml() -> None:
    """Regression: the PDF grand total MUST equal XML LegalMonetaryTotal/PayableAmount.

    The PDF view model formats in BeNeLux notation while the UBL XML uses ASCII,
    so cross-checks parse both sides back to Decimal before comparing.
    """
    vm = _build_view_model(SAMPLE_INVOICE)
    xml = generate_ubl(SAMPLE_INVOICE)
    root = ET.fromstring(xml)
    lmt = root.find(f"{{{CAC}}}LegalMonetaryTotal")
    assert lmt is not None
    payable = lmt.find(f"{{{CBC}}}PayableAmount")
    assert payable is not None
    assert payable.text is not None
    assert _parse_benelux(vm["grand_total"]) == Decimal(payable.text)
    tax_total_el = root.find(f"{{{CAC}}}TaxTotal/{{{CBC}}}TaxAmount")
    assert tax_total_el is not None
    assert tax_total_el.text is not None
    assert _parse_benelux(vm["tax_total"]) == Decimal(tax_total_el.text)


def test_view_model_totals_match_ubl_xml_mixed_rates() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "S", "tax_percent": 21},
            {"id": "2", "quantity": 1, "unit_price": 200.0, "tax_category": "S", "tax_percent": 6},
        ],
    }
    vm = _build_view_model(inv)
    xml = generate_ubl(inv)
    root = ET.fromstring(xml)
    payable = root.find(f"{{{CAC}}}LegalMonetaryTotal/{{{CBC}}}PayableAmount")
    assert payable is not None
    assert payable.text is not None
    assert _parse_benelux(vm["grand_total"]) == Decimal(payable.text)


def test_view_model_omits_payment_means_when_absent() -> None:
    inv = {k: v for k, v in SAMPLE_INVOICE.items() if k != "payment_means"}
    vm = _build_view_model(inv)
    assert vm["payment_means"] is None


def test_view_model_includes_epc_qr_for_eur_credit_transfer() -> None:
    vm = _build_view_model(SAMPLE_INVOICE)
    assert vm["epc_qr_svg"] is not None
    assert vm["epc_qr_svg"].startswith("<svg")

    from peppol_sender.pdf import _env

    html = _env.get_template("invoice.html").render(**vm)
    assert 'class="payment-qr"' in html  # QR container rendered into markup
    assert "Scan with your banking app" in html


def test_view_model_omits_epc_qr_for_non_eur_invoice() -> None:
    inv = {**SAMPLE_INVOICE, "currency": "USD"}
    vm = _build_view_model(inv)
    assert vm["epc_qr_svg"] is None

    from peppol_sender.pdf import _env

    html = _env.get_template("invoice.html").render(**vm)
    assert 'class="payment-qr"' not in html
    assert "Scan with your banking app" not in html


def test_view_model_line_extension_amount_override() -> None:
    """Explicit line_extension_amount overrides the quantity * unit_price default."""
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {
                "id": "1",
                "quantity": 5,
                "unit_price": 100.0,
                "line_extension_amount": 400.0,  # discount
                "tax_category": "E",
                "tax_percent": 0,
            }
        ],
    }
    vm = _build_view_model(inv)
    assert vm["lines"][0]["line_total"] == "400,00"
    assert vm["subtotal"] == "400,00"


# --- language / translation ---


def test_view_model_defaults_to_english_when_language_absent() -> None:
    vm = _build_view_model(SAMPLE_INVOICE)
    assert vm["language"] == "en"
    assert vm["labels"]["invoice"] == "Invoice"
    assert vm["labels"]["total_due"] == "Total due"
    # Unit code HUR → "hour" in EN
    assert vm["lines"][0]["unit_label"] == "hour"


def test_view_model_dutch_labels_and_unit() -> None:
    inv = {**SAMPLE_INVOICE, "language": "nl"}
    vm = _build_view_model(inv)
    assert vm["language"] == "nl"
    assert vm["labels"]["invoice"] == "Factuur"
    assert vm["labels"]["total_due"] == "Te betalen"
    assert vm["lines"][0]["unit_label"] == "uur"


def test_view_model_french_labels_and_unit() -> None:
    inv = {**SAMPLE_INVOICE, "language": "fr"}
    vm = _build_view_model(inv)
    assert vm["labels"]["invoice"] == "Facture"
    assert vm["labels"]["subtotal"] == "Sous-total"
    assert vm["lines"][0]["unit_label"] == "heure"


def test_view_model_german_labels_and_unit() -> None:
    inv = {**SAMPLE_INVOICE, "language": "de"}
    vm = _build_view_model(inv)
    assert vm["labels"]["invoice"] == "Rechnung"
    assert vm["labels"]["description"] == "Beschreibung"
    assert vm["lines"][0]["unit_label"] == "Stunde"


def test_view_model_unknown_language_falls_back_to_english() -> None:
    inv = {**SAMPLE_INVOICE, "language": "zz"}
    vm = _build_view_model(inv)
    assert vm["labels"]["invoice"] == "Invoice"
    assert vm["lines"][0]["unit_label"] == "hour"


def test_view_model_case_insensitive_language_code() -> None:
    inv = {**SAMPLE_INVOICE, "language": "NL"}
    vm = _build_view_model(inv)
    assert vm["language"] == "nl"
    assert vm["labels"]["invoice"] == "Factuur"


def test_rendered_html_contains_translated_labels_nl() -> None:
    from peppol_sender.pdf import _env

    inv = {**SAMPLE_INVOICE, "language": "nl"}
    vm = _build_view_model(inv)
    html = _env.get_template("invoice.html").render(**vm)
    assert "Factuur" in html
    assert "Omschrijving" in html
    assert "Te betalen" in html
    assert "uur" in html  # translated unit code
    # The raw code HUR should NOT appear as a standalone cell value
    assert ">HUR<" not in html


def test_rendered_html_contains_translated_labels_de() -> None:
    from peppol_sender.pdf import _env

    inv = {**SAMPLE_INVOICE, "language": "de"}
    vm = _build_view_model(inv)
    html = _env.get_template("invoice.html").render(**vm)
    assert "Rechnung" in html
    assert "Beschreibung" in html
    assert "Gesamtbetrag" in html
    assert "Stunde" in html


def test_rendered_html_contains_translated_labels_fr() -> None:
    from peppol_sender.pdf import _env

    inv = {**SAMPLE_INVOICE, "language": "fr"}
    vm = _build_view_model(inv)
    html = _env.get_template("invoice.html").render(**vm)
    assert "Facture" in html
    assert "Sous-total" in html
    assert "Total à payer" in html
    assert "heure" in html


def test_rendered_html_credit_note_title() -> None:
    from peppol_sender.pdf import _env

    cn = {**SAMPLE_INVOICE, "credit_note_type_code": "381", "language": "en"}
    cn.pop("due_date", None)
    vm = _build_view_model(cn)
    html = _env.get_template("invoice.html").render(**vm)
    assert "Credit Note" in html
    assert ">Invoice<" not in html


def test_rendered_html_credit_note_title_nl() -> None:
    from peppol_sender.pdf import _env

    cn = {**SAMPLE_INVOICE, "credit_note_type_code": "381", "language": "nl"}
    cn.pop("due_date", None)
    vm = _build_view_model(cn)
    html = _env.get_template("invoice.html").render(**vm)
    assert "Creditnota" in html
    assert ">Factuur<" not in html


def test_rendered_html_unknown_language_still_renders() -> None:
    from peppol_sender.pdf import _env

    inv = {**SAMPLE_INVOICE, "language": "zz"}
    vm = _build_view_model(inv)
    html = _env.get_template("invoice.html").render(**vm)
    # Falls back to English labels; nothing raises
    assert "Invoice" in html
    assert "Description" in html


def test_dec_rounding_matches_ubl() -> None:
    """Guardrail: pdf._dec and ubl._dec round identically."""
    from peppol_sender.pdf import _dec as pdf_dec
    from peppol_sender.ubl import _dec as ubl_dec

    for value in ("1.005", "0.015", "99.999", 33.33, Decimal("12.345")):
        assert pdf_dec(value) == ubl_dec(value), f"mismatch for {value!r}"


# --- render smoke ---


def test_render_pdf_returns_pdf_bytes() -> None:
    pdf = render_pdf(SAMPLE_INVOICE)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000  # real PDFs are at least a couple of KB


def test_render_pdf_survives_minimal_invoice() -> None:
    """No due_date, no payment_means, no service_date — still renders."""
    minimal = {
        "invoice_number": "MIN-1",
        "issue_date": "2026-04-14",
        "currency": "EUR",
        "seller": {"name": "S", "country": "BE"},
        "buyer": {"name": "B", "country": "NL"},
        "lines": [
            {"id": "1", "description": "x", "quantity": 1, "unit_price": 10.0, "tax_category": "E", "tax_percent": 0}
        ],
    }
    pdf = render_pdf(minimal)
    assert pdf.startswith(b"%PDF-")
