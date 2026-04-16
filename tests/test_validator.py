"""Tests for peppol_sender.validator — structural and XSD validation."""

from peppol_sender.ubl import generate_credit_note, generate_ubl
from peppol_sender.validator import _schema_for, validate_basic, validate_xsd

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


# --- LOCAL-F001 local date format check ---


def test_f001_passes_on_valid_dates() -> None:
    xml = generate_ubl(VALID_INVOICE)
    assert "LOCAL-F001" not in _rule_ids(validate_basic(xml))


def test_f001_triggers_on_malformed_issue_date() -> None:
    xml = generate_ubl({**VALID_INVOICE, "issue_date": "not-a-date"})
    rules = [r for r in validate_basic(xml) if r["id"] == "LOCAL-F001"]
    assert any("IssueDate" in r["location"] for r in rules)


def test_f001_triggers_on_prefixed_line_service_date() -> None:
    """Regression: reproduces the '262025-12-16' garbage date bug."""
    invoice = {
        **VALID_INVOICE,
        "lines": [
            {
                "id": "1",
                "quantity": 1,
                "unit_price": 100.0,
                "tax_category": "E",
                "tax_percent": 0,
                "service_date": "262025-12-16",
            }
        ],
    }
    xml = generate_ubl(invoice)
    rules = [r for r in validate_basic(xml) if r["id"] == "LOCAL-F001"]
    locations = [r["location"] for r in rules]
    assert "/*:Invoice/*:StartDate" in locations
    assert "/*:Invoice/*:EndDate" in locations


def test_f001_triggers_on_empty_issue_date() -> None:
    """Empty string issue_date (e.g. unfilled webapp input) must not slip through."""
    xml = generate_ubl({**VALID_INVOICE, "issue_date": ""})
    rules = [r for r in validate_basic(xml) if r["id"] == "LOCAL-F001"]
    assert any("IssueDate" in r["location"] for r in rules)


# --- Credit note validation ---


VALID_CREDIT_NOTE = {
    "invoice_number": "CN-001",
    "issue_date": "2025-02-01",
    "credit_note_type_code": "381",
    "currency": "EUR",
    "billing_reference": {"id": "INV-001", "issue_date": "2025-01-01"},
    "seller": VALID_INVOICE["seller"],
    "buyer": VALID_INVOICE["buyer"],
    "lines": VALID_INVOICE["lines"],
}


def test_validate_basic_accepts_valid_credit_note() -> None:
    xml = generate_credit_note(VALID_CREDIT_NOTE)
    rules = validate_basic(xml)
    assert rules == []


def test_validate_basic_missing_credit_note_type_code() -> None:
    # Generate a valid credit note then mutate the XML to strip the type code.
    xml = generate_credit_note(VALID_CREDIT_NOTE).replace(b"<cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>", b"")
    rules = validate_basic(xml)
    assert any(r["id"] == "LOCAL-MISSING-CreditNoteTypeCode" for r in rules)


def test_validate_basic_missing_credit_note_line() -> None:
    # Build a credit note with no lines to trigger the missing-line rule.
    xml = generate_credit_note({**VALID_CREDIT_NOTE, "lines": []})
    rules = validate_basic(xml)
    assert any(r["id"] == "LOCAL-MISSING-CreditNoteLine" for r in rules)


def test_validate_basic_unknown_root() -> None:
    xml = b'<?xml version="1.0"?><Foo xmlns="urn:x"/>'
    rules = validate_basic(xml)
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-UNKNOWN-ROOT"
    assert rules[0]["type"] == "FATAL"


def test_validate_basic_error_locations_use_credit_note_root() -> None:
    # When a credit note is missing elements, the location strings should
    # report /*:CreditNote/... not /*:Invoice/... so users aren't confused.
    xml = generate_credit_note({**VALID_CREDIT_NOTE, "lines": []})
    rules = [r for r in validate_basic(xml) if r["id"].startswith("LOCAL-MISSING")]
    for r in rules:
        assert r["location"].startswith("/*:CreditNote/"), r["location"]


def test_validate_xsd_selects_credit_note_schema() -> None:
    xml = generate_credit_note(VALID_CREDIT_NOTE)
    assert validate_xsd(xml) == []


def test_validate_xsd_unknown_root_returns_fatal() -> None:
    # Bypass validate_basic and call validate_xsd directly on an unknown root.
    xml = b'<?xml version="1.0"?><Foo xmlns="urn:x"/>'
    rules = validate_xsd(xml)
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-UNKNOWN-ROOT"


def test_validate_xsd_unparseable_returns_parse_error() -> None:
    rules = validate_xsd(b"<not-xml")
    assert len(rules) == 1
    assert rules[0]["id"] == "LOCAL-XML-PARSE"


def test_schema_cache_loads_each_doc_type_once() -> None:
    _schema_for.cache_clear()
    _schema_for("Invoice")
    _schema_for("Invoice")
    _schema_for("CreditNote")
    _schema_for("CreditNote")
    info = _schema_for.cache_info()
    assert info.hits == 2
    assert info.misses == 2
