"""Tests for peppol_sender.ubl — UBL 2.1 invoice generation."""

from xml.etree import ElementTree as ET

from peppol_sender.ubl import generate_ubl

NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"


def _parse(invoice: dict) -> ET.Element:
    xml_bytes = generate_ubl(invoice)
    return ET.fromstring(xml_bytes)


def _find(root: ET.Element, tag: str) -> ET.Element | None:
    return root.find(f".//{{{NS}}}{tag}")


SAMPLE_INVOICE = {
    "invoice_number": "INV-TEST-001",
    "issue_date": "2025-01-15",
    "currency": "EUR",
    "seller": {"name": "Test Seller"},
    "buyer": {"name": "Test Buyer"},
    "lines": [
        {
            "id": "1",
            "description": "Consulting",
            "quantity": 2,
            "unit": "HUR",
            "unit_price": 150.00,
        }
    ],
}


def test_required_elements_present() -> None:
    root = _parse(SAMPLE_INVOICE)
    for tag in ["ID", "IssueDate", "AccountingSupplierParty", "AccountingCustomerParty", "InvoiceLine"]:
        assert _find(root, tag) is not None, f"Missing required element: {tag}"


def test_header_values() -> None:
    root = _parse(SAMPLE_INVOICE)
    assert _find(root, "ID") is not None
    assert _find(root, "ID").text == "INV-TEST-001"  # type: ignore[union-attr]
    assert _find(root, "IssueDate") is not None
    assert _find(root, "IssueDate").text == "2025-01-15"  # type: ignore[union-attr]


def test_seller_name() -> None:
    root = _parse(SAMPLE_INVOICE)
    supplier = _find(root, "AccountingSupplierParty")
    assert supplier is not None
    name = supplier.find(f".//{{{NS}}}Name")
    assert name is not None
    assert name.text == "Test Seller"


def test_buyer_name() -> None:
    root = _parse(SAMPLE_INVOICE)
    customer = _find(root, "AccountingCustomerParty")
    assert customer is not None
    name = customer.find(f".//{{{NS}}}Name")
    assert name is not None
    assert name.text == "Test Buyer"


def test_defaults_applied() -> None:
    root = _parse({})
    assert _find(root, "ID") is not None
    assert _find(root, "ID").text == "INV-0001"  # type: ignore[union-attr]
    supplier = _find(root, "AccountingSupplierParty")
    assert supplier is not None
    name = supplier.find(f".//{{{NS}}}Name")
    assert name is not None
    assert name.text == "Seller"


def test_line_item_mapping() -> None:
    root = _parse(SAMPLE_INVOICE)
    line = _find(root, "InvoiceLine")
    assert line is not None

    lid = line.find(f"{{{NS}}}ID")
    assert lid is not None and lid.text == "1"

    qty = line.find(f"{{{NS}}}InvoicedQuantity")
    assert qty is not None
    assert qty.text == "2"
    assert qty.get("unitCode") == "HUR"

    item_name = line.find(f".//{{{NS}}}Item/{{{NS}}}Name")
    assert item_name is not None and item_name.text == "Consulting"

    price = line.find(f".//{{{NS}}}PriceAmount")
    assert price is not None
    assert price.text == "150.00"
    assert price.get("currencyID") == "EUR"


def test_line_extension_amount_calculated() -> None:
    root = _parse(SAMPLE_INVOICE)
    ext = _find(root, "LineExtensionAmount")
    assert ext is not None
    assert ext.text == "300.00"  # 2 * 150.00
    assert ext.get("currencyID") == "EUR"


def test_line_extension_amount_explicit() -> None:
    invoice = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 2, "unit_price": 150.00, "line_extension_amount": 275.00}],
    }
    root = _parse(invoice)
    ext = _find(root, "LineExtensionAmount")
    assert ext is not None
    assert ext.text == "275.00"


def test_default_unit_code() -> None:
    invoice = {**SAMPLE_INVOICE, "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00}]}
    root = _parse(invoice)
    qty = _find(root, "InvoicedQuantity")
    assert qty is not None
    assert qty.get("unitCode") == "EA"


def test_output_is_utf8_bytes() -> None:
    result = generate_ubl(SAMPLE_INVOICE)
    assert isinstance(result, bytes)
    assert b"utf-8" in result[:100].lower()
