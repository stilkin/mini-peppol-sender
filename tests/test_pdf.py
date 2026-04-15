"""Tests for peppol_sender.pdf — invoice PDF rendering and view model."""

from decimal import Decimal
from xml.etree import ElementTree as ET

from peppol_sender.pdf import _build_view_model, render_pdf
from peppol_sender.ubl import generate_ubl

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


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
    assert vm["subtotal"] == "1000.00"
    assert vm["tax_total"] == "0.00"
    assert vm["grand_total"] == "1000.00"
    assert vm["currency"] == "EUR"
    assert len(vm["lines"]) == 1
    assert vm["lines"][0]["line_total"] == "1000.00"
    assert vm["lines"][0]["service_date"] == "2026-04-10"


def test_view_model_with_standard_vat() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 2, "unit_price": 50.0, "tax_category": "S", "tax_percent": 21}],
    }
    vm = _build_view_model(inv)
    # 2 * 50 = 100; 21% = 21.00; total 121.00
    assert vm["subtotal"] == "100.00"
    assert vm["tax_total"] == "21.00"
    assert vm["grand_total"] == "121.00"


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
    assert vm["subtotal"] == "300.00"
    assert vm["tax_total"] == "33.00"
    assert vm["grand_total"] == "333.00"


def test_view_model_totals_match_ubl_xml() -> None:
    """Regression: the PDF grand total MUST equal XML LegalMonetaryTotal/PayableAmount."""
    vm = _build_view_model(SAMPLE_INVOICE)
    xml = generate_ubl(SAMPLE_INVOICE)
    root = ET.fromstring(xml)
    lmt = root.find(f"{{{CAC}}}LegalMonetaryTotal")
    assert lmt is not None
    payable = lmt.find(f"{{{CBC}}}PayableAmount")
    assert payable is not None
    assert payable.text == vm["grand_total"]
    tax_total_el = root.find(f"{{{CAC}}}TaxTotal/{{{CBC}}}TaxAmount")
    assert tax_total_el is not None
    assert tax_total_el.text == vm["tax_total"]


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
    assert payable.text == vm["grand_total"]


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
    assert vm["lines"][0]["line_total"] == "400.00"
    assert vm["subtotal"] == "400.00"


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
