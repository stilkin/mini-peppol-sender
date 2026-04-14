"""Tests for peppol_sender.validator — structural and XSD validation."""

from peppol_sender.ubl import generate_ubl
from peppol_sender.validator import validate_basic, validate_xsd

VALID_INVOICE = {
    "invoice_number": "INV-001",
    "issue_date": "2025-01-01",
    "due_date": "2025-02-01",
    "currency": "EUR",
    "seller": {
        "name": "Seller",
        "registration_name": "Seller BV",
        "endpoint_id": "BE0123456789",
        "endpoint_scheme": "0208",
        "country": "BE",
    },
    "buyer": {
        "name": "Buyer",
        "registration_name": "Buyer BV",
        "endpoint_id": "NL987654321",
        "endpoint_scheme": "0208",
        "country": "NL",
    },
    "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "E", "tax_percent": 0}],
}


# --- validate_basic ---


def test_valid_xml_returns_no_rules() -> None:
    xml = generate_ubl(VALID_INVOICE)
    rules = validate_basic(xml)
    assert rules == []


def test_missing_all_elements() -> None:
    xml = b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"></Invoice>'
    rules = validate_basic(xml)
    assert len(rules) == 11
    assert all(r["type"] == "FATAL" for r in rules)


def test_single_missing_element() -> None:
    xml = (
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"'
        b' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
        b' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">'
        b"<cbc:CustomizationID>x</cbc:CustomizationID>"
        b"<cbc:ProfileID>x</cbc:ProfileID>"
        b"<cbc:ID>1</cbc:ID><cbc:IssueDate>2025-01-01</cbc:IssueDate>"
        b"<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"
        b"<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        b"<cac:AccountingSupplierParty/><cac:AccountingCustomerParty/>"
        b"<cac:TaxTotal/><cac:LegalMonetaryTotal/>"
        b"</Invoice>"
    )
    rules = validate_basic(xml)
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-MISSING-InvoiceLine"


def test_unparseable_xml() -> None:
    rules = validate_basic(b"not xml at all")
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-XML-PARSE"
    assert rules[0]["type"] == "FATAL"


def test_empty_bytes() -> None:
    rules = validate_basic(b"")
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-XML-PARSE"


# --- validate_xsd ---


def test_xsd_valid_invoice() -> None:
    xml = generate_ubl(VALID_INVOICE)
    rules = validate_xsd(xml)
    assert rules == []


def test_xsd_invalid_invoice() -> None:
    # Bare Invoice element missing all required children
    xml = b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"></Invoice>'
    rules = validate_xsd(xml)
    assert len(rules) > 0
    assert all(r["type"] == "FATAL" for r in rules)
    assert all(r["id"] == "XSD-VALIDATION" for r in rules)


# --- BR-50 local check (credit transfer requires IBAN) ---


_PAYMENT_MEANS_SAMPLE = {
    "code": "30",
    "iban": "BE68539007547034",
    "bic": "BBRUBEBB",
    "account_name": "Seller BV",
}


def _rule_ids(rules: list[dict]) -> list[str]:
    return [r["id"] for r in rules]


def test_br50_passes_on_present_iban() -> None:
    xml = generate_ubl({**VALID_INVOICE, "payment_means": _PAYMENT_MEANS_SAMPLE})
    assert "LOCAL-BR-50" not in _rule_ids(validate_basic(xml))


def test_br50_triggers_on_missing_iban() -> None:
    xml = generate_ubl({**VALID_INVOICE, "payment_means": {"code": "30"}})
    rules = validate_basic(xml)
    br50 = [r for r in rules if r["id"] == "LOCAL-BR-50"]
    assert len(br50) == 1
    assert br50[0]["type"] == "FATAL"


def test_br50_applies_to_code_58() -> None:
    xml = generate_ubl({**VALID_INVOICE, "payment_means": {"code": "58"}})
    assert "LOCAL-BR-50" in _rule_ids(validate_basic(xml))


def test_br50_not_applied_to_non_credit_transfer_code() -> None:
    xml = generate_ubl({**VALID_INVOICE, "payment_means": {"code": "10"}})
    assert "LOCAL-BR-50" not in _rule_ids(validate_basic(xml))


def test_br50_not_applied_when_payment_means_absent() -> None:
    xml = generate_ubl(VALID_INVOICE)
    assert "LOCAL-BR-50" not in _rule_ids(validate_basic(xml))


def test_br50_triggers_on_empty_iban_element() -> None:
    # Hand-crafted XML with empty PayeeFinancialAccount/ID
    xml = generate_ubl({**VALID_INVOICE, "payment_means": {**_PAYMENT_MEANS_SAMPLE, "iban": ""}})
    # Empty iban means generator skips the PayeeFinancialAccount entirely, so
    # the rule still fires (missing IBAN for credit transfer code).
    assert "LOCAL-BR-50" in _rule_ids(validate_basic(xml))
