"""Tests for peppol_sender.validator — basic structural validation."""

from peppol_sender.ubl import generate_ubl
from peppol_sender.validator import validate_basic

VALID_INVOICE = {
    "invoice_number": "INV-001",
    "issue_date": "2025-01-01",
    "seller": {"name": "Seller"},
    "buyer": {"name": "Buyer"},
    "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00}],
}


def test_valid_xml_returns_no_rules() -> None:
    xml = generate_ubl(VALID_INVOICE)
    rules = validate_basic(xml)
    assert rules == []


def test_single_missing_element() -> None:
    """XML with all required elements except InvoiceLine."""
    xml = (
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
        b"<ID>1</ID><IssueDate>2025-01-01</IssueDate>"
        b"<AccountingSupplierParty/><AccountingCustomerParty/>"
        b"</Invoice>"
    )
    rules = validate_basic(xml)
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-MISSING-InvoiceLine"


def test_missing_elements_detected() -> None:
    # Minimal XML with only the root element — missing all required children
    xml = b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"></Invoice>'
    rules = validate_basic(xml)
    assert len(rules) == 5
    ids = {r["id"] for r in rules}
    assert "LOCAL-MISSING-ID" in ids
    assert "LOCAL-MISSING-IssueDate" in ids
    assert "LOCAL-MISSING-AccountingSupplierParty" in ids
    assert "LOCAL-MISSING-AccountingCustomerParty" in ids
    assert "LOCAL-MISSING-InvoiceLine" in ids
    for r in rules:
        assert r["type"] == "FATAL"


def test_partial_missing_elements() -> None:
    xml = (
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
        b"<ID>1</ID><IssueDate>2025-01-01</IssueDate>"
        b"</Invoice>"
    )
    rules = validate_basic(xml)
    assert len(rules) == 3
    ids = {r["id"] for r in rules}
    assert "LOCAL-MISSING-AccountingSupplierParty" in ids
    assert "LOCAL-MISSING-AccountingCustomerParty" in ids
    assert "LOCAL-MISSING-InvoiceLine" in ids


def test_unparseable_xml() -> None:
    rules = validate_basic(b"not xml at all")
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-XML-PARSE"
    assert rules[0]["type"] == "FATAL"


def test_empty_bytes() -> None:
    rules = validate_basic(b"")
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-XML-PARSE"
    assert rules[0]["type"] == "FATAL"
