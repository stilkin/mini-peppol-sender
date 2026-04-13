"""Tests for peppol_sender.ubl — UBL 2.1 invoice generation."""

from xml.etree import ElementTree as ET

from peppol_sender.ubl import generate_ubl

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


def _parse(invoice: dict) -> ET.Element:
    return ET.fromstring(generate_ubl(invoice))


def _find(root: ET.Element, path: str) -> ET.Element | None:
    """Find element using simplified path like 'cbc:ID' or 'cac:TaxTotal/cbc:TaxAmount'."""
    parts = path.split("/")
    xpath = ""
    for part in parts:
        if part.startswith("cbc:"):
            xpath += f".//{{{CBC}}}{part[4:]}"
        elif part.startswith("cac:"):
            xpath += f".//{{{CAC}}}{part[4:]}"
        else:
            xpath += f".//{part}"
    return root.find(xpath)


SAMPLE_INVOICE = {
    "invoice_number": "INV-TEST-001",
    "issue_date": "2025-01-15",
    "due_date": "2025-02-15",
    "invoice_type_code": "380",
    "currency": "EUR",
    "payment_terms": "Net 30",
    "seller": {
        "name": "Test Seller",
        "registration_name": "Test Seller BV",
        "endpoint_id": "BE0123456789",
        "endpoint_scheme": "0208",
        "country": "BE",
        "street": "Main St 1",
        "city": "Brussels",
        "postal_code": "1000",
    },
    "buyer": {
        "name": "Test Buyer",
        "registration_name": "Test Buyer BV",
        "endpoint_id": "NL987654321",
        "endpoint_scheme": "0208",
        "vat": "NL987654321B01",
        "country": "NL",
    },
    "lines": [
        {
            "id": "1",
            "description": "Consulting",
            "quantity": 2,
            "unit": "HUR",
            "unit_price": 150.00,
            "tax_category": "E",
            "tax_percent": 0,
        }
    ],
}


# --- Document header ---


def test_required_header_fields() -> None:
    root = _parse(SAMPLE_INVOICE)
    for tag in ["CustomizationID", "ProfileID", "ID", "IssueDate", "InvoiceTypeCode", "DocumentCurrencyCode"]:
        assert _find(root, f"cbc:{tag}") is not None, f"Missing: {tag}"


def test_header_values() -> None:
    root = _parse(SAMPLE_INVOICE)
    assert _find(root, "cbc:ID").text == "INV-TEST-001"  # type: ignore[union-attr]
    assert _find(root, "cbc:IssueDate").text == "2025-01-15"  # type: ignore[union-attr]
    assert _find(root, "cbc:DueDate").text == "2025-02-15"  # type: ignore[union-attr]
    assert _find(root, "cbc:InvoiceTypeCode").text == "380"  # type: ignore[union-attr]
    assert _find(root, "cbc:DocumentCurrencyCode").text == "EUR"  # type: ignore[union-attr]


def test_due_date_omitted_when_not_provided() -> None:
    inv = {**SAMPLE_INVOICE}
    del inv["due_date"]
    root = _parse(inv)
    assert _find(root, "cbc:DueDate") is None


def test_payment_terms() -> None:
    root = _parse(SAMPLE_INVOICE)
    pt = root.find(f".//{{{CAC}}}PaymentTerms/{{{CBC}}}Note")
    assert pt is not None
    assert pt.text == "Net 30"


# --- Party details ---


def test_seller_party() -> None:
    root = _parse(SAMPLE_INVOICE)
    supplier = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert supplier is not None

    endpoint = supplier.find(f"{{{CBC}}}EndpointID")
    assert endpoint is not None
    assert endpoint.text == "BE0123456789"
    assert endpoint.get("schemeID") == "0208"

    reg_name = supplier.find(f".//{{{CAC}}}PartyLegalEntity/{{{CBC}}}RegistrationName")
    assert reg_name is not None
    assert reg_name.text == "Test Seller BV"

    country = supplier.find(f".//{{{CAC}}}PostalAddress/{{{CAC}}}Country/{{{CBC}}}IdentificationCode")
    assert country is not None
    assert country.text == "BE"


def test_buyer_party_with_vat() -> None:
    root = _parse(SAMPLE_INVOICE)
    customer = root.find(f".//{{{CAC}}}AccountingCustomerParty/{{{CAC}}}Party")
    assert customer is not None

    vat = customer.find(f".//{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID")
    assert vat is not None
    assert vat.text == "NL987654321B01"


def test_legal_entity_company_id() -> None:
    """BT-30/BT-47: PartyLegalEntity/CompanyID with optional schemeID."""
    seller = dict(SAMPLE_INVOICE["seller"])  # type: ignore[arg-type]
    seller["legal_id"] = "0674415660"
    seller["legal_id_scheme"] = "0208"
    buyer = dict(SAMPLE_INVOICE["buyer"])  # type: ignore[arg-type]
    buyer["legal_id"] = "987654321"  # no scheme
    inv = {**SAMPLE_INVOICE, "seller": seller, "buyer": buyer}
    root = _parse(inv)

    seller_party = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert seller_party is not None
    seller_cid = seller_party.find(f".//{{{CAC}}}PartyLegalEntity/{{{CBC}}}CompanyID")
    assert seller_cid is not None
    assert seller_cid.text == "0674415660"
    assert seller_cid.get("schemeID") == "0208"

    buyer_party = root.find(f".//{{{CAC}}}AccountingCustomerParty/{{{CAC}}}Party")
    assert buyer_party is not None
    buyer_cid = buyer_party.find(f".//{{{CAC}}}PartyLegalEntity/{{{CBC}}}CompanyID")
    assert buyer_cid is not None
    assert buyer_cid.text == "987654321"
    assert buyer_cid.get("schemeID") is None


def test_legal_entity_no_company_id_when_absent() -> None:
    root = _parse(SAMPLE_INVOICE)
    seller = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert seller is not None
    assert seller.find(f".//{{{CAC}}}PartyLegalEntity/{{{CBC}}}CompanyID") is None


def test_party_contact_emitted() -> None:
    """BT-41..43 (seller) / BT-56..58 (buyer): Contact block is optional."""
    seller = dict(SAMPLE_INVOICE["seller"])  # type: ignore[arg-type]
    seller["contact_name"] = "Jane Doe"
    seller["contact_email"] = "jane@example.be"
    seller["contact_phone"] = "+32 14 00 00 00"
    inv = {**SAMPLE_INVOICE, "seller": seller}
    root = _parse(inv)

    contact = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party/{{{CAC}}}Contact")
    assert contact is not None
    assert contact.find(f"{{{CBC}}}Name").text == "Jane Doe"  # type: ignore[union-attr]
    assert contact.find(f"{{{CBC}}}ElectronicMail").text == "jane@example.be"  # type: ignore[union-attr]
    assert contact.find(f"{{{CBC}}}Telephone").text == "+32 14 00 00 00"  # type: ignore[union-attr]


def test_party_contact_omitted_when_absent() -> None:
    root = _parse(SAMPLE_INVOICE)
    seller_party = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert seller_party is not None
    assert seller_party.find(f"{{{CAC}}}Contact") is None


def test_party_contact_partial() -> None:
    """Only the fields that are set are emitted."""
    seller = dict(SAMPLE_INVOICE["seller"])  # type: ignore[arg-type]
    seller["contact_email"] = "only@example.be"
    inv = {**SAMPLE_INVOICE, "seller": seller}
    root = _parse(inv)

    contact = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party/{{{CAC}}}Contact")
    assert contact is not None
    assert contact.find(f"{{{CBC}}}ElectronicMail").text == "only@example.be"  # type: ignore[union-attr]
    assert contact.find(f"{{{CBC}}}Name") is None
    assert contact.find(f"{{{CBC}}}Telephone") is None


def test_seller_no_vat_omits_tax_scheme() -> None:
    root = _parse(SAMPLE_INVOICE)
    supplier = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert supplier is not None
    assert supplier.find(f".//{{{CAC}}}PartyTaxScheme") is None


def test_address_fields() -> None:
    root = _parse(SAMPLE_INVOICE)
    supplier = root.find(f".//{{{CAC}}}AccountingSupplierParty/{{{CAC}}}Party")
    assert supplier is not None
    addr = supplier.find(f".//{{{CAC}}}PostalAddress")
    assert addr is not None
    assert addr.find(f"{{{CBC}}}StreetName").text == "Main St 1"  # type: ignore[union-attr]
    assert addr.find(f"{{{CBC}}}CityName").text == "Brussels"  # type: ignore[union-attr]
    assert addr.find(f"{{{CBC}}}PostalZone").text == "1000"  # type: ignore[union-attr]


# --- Tax ---


def test_tax_exempt() -> None:
    root = _parse(SAMPLE_INVOICE)
    tax_amt = root.find(f".//{{{CAC}}}TaxTotal/{{{CBC}}}TaxAmount")
    assert tax_amt is not None
    assert tax_amt.text == "0.00"

    subtotal = root.find(f".//{{{CAC}}}TaxSubtotal")
    assert subtotal is not None
    cat_id = subtotal.find(f".//{{{CAC}}}TaxCategory/{{{CBC}}}ID")
    assert cat_id is not None and cat_id.text == "E"

    reason = subtotal.find(f".//{{{CAC}}}TaxCategory/{{{CBC}}}TaxExemptionReason")
    assert reason is not None and reason.text == "Exempt"


def test_tax_with_vat() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "S", "tax_percent": 21}],
    }
    root = _parse(inv)
    tax_amt = root.find(f".//{{{CAC}}}TaxTotal/{{{CBC}}}TaxAmount")
    assert tax_amt is not None
    assert tax_amt.text == "21.00"


def test_tax_mixed_rates() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "S", "tax_percent": 21},
            {"id": "2", "quantity": 1, "unit_price": 50.00, "tax_category": "S", "tax_percent": 6},
        ],
    }
    root = _parse(inv)
    tax_amt = root.find(f".//{{{CAC}}}TaxTotal/{{{CBC}}}TaxAmount")
    assert tax_amt is not None
    assert tax_amt.text == "24.00"  # 21 + 3


# --- Totals ---


def test_legal_monetary_total() -> None:
    root = _parse(SAMPLE_INVOICE)
    lmt = root.find(f".//{{{CAC}}}LegalMonetaryTotal")
    assert lmt is not None

    line_ext = lmt.find(f"{{{CBC}}}LineExtensionAmount")
    assert line_ext is not None and line_ext.text == "300.00"

    tax_excl = lmt.find(f"{{{CBC}}}TaxExclusiveAmount")
    assert tax_excl is not None and tax_excl.text == "300.00"

    # VAT-exempt: tax is 0, so inclusive == exclusive
    tax_incl = lmt.find(f"{{{CBC}}}TaxInclusiveAmount")
    assert tax_incl is not None and tax_incl.text == "300.00"

    payable = lmt.find(f"{{{CBC}}}PayableAmount")
    assert payable is not None and payable.text == "300.00"


def test_legal_monetary_total_with_vat() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "S", "tax_percent": 21}],
    }
    root = _parse(inv)
    lmt = root.find(f".//{{{CAC}}}LegalMonetaryTotal")
    assert lmt is not None
    assert lmt.find(f"{{{CBC}}}TaxInclusiveAmount").text == "121.00"  # type: ignore[union-attr]
    assert lmt.find(f"{{{CBC}}}PayableAmount").text == "121.00"  # type: ignore[union-attr]


# --- Line items ---


def test_line_item_tax_category() -> None:
    root = _parse(SAMPLE_INVOICE)
    ctc = root.find(f".//{{{CAC}}}InvoiceLine//{{{CAC}}}ClassifiedTaxCategory")
    assert ctc is not None
    assert ctc.find(f"{{{CBC}}}ID").text == "E"  # type: ignore[union-attr]
    assert ctc.find(f"{{{CBC}}}Percent").text == "0"  # type: ignore[union-attr]
    assert ctc.find(f".//{{{CAC}}}TaxScheme/{{{CBC}}}ID").text == "VAT"  # type: ignore[union-attr]


def test_line_extension_amount_calculated() -> None:
    root = _parse(SAMPLE_INVOICE)
    ext = root.find(f".//{{{CAC}}}InvoiceLine/{{{CBC}}}LineExtensionAmount")
    assert ext is not None
    assert ext.text == "300.00"  # 2 * 150
    assert ext.get("currencyID") == "EUR"


def test_line_extension_amount_explicit() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {
                "id": "1",
                "quantity": 2,
                "unit_price": 150.00,
                "line_extension_amount": 275.00,
                "tax_category": "E",
                "tax_percent": 0,
            },
        ],
    }
    root = _parse(inv)
    ext = root.find(f".//{{{CAC}}}InvoiceLine/{{{CBC}}}LineExtensionAmount")
    assert ext is not None
    assert ext.text == "275.00"


def test_default_unit_code() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "E", "tax_percent": 0}],
    }
    root = _parse(inv)
    qty = root.find(f".//{{{CAC}}}InvoiceLine/{{{CBC}}}InvoicedQuantity")
    assert qty is not None
    assert qty.get("unitCode") == "EA"


# --- Defaults ---


def test_defaults_applied() -> None:
    root = _parse({})
    assert _find(root, "cbc:ID").text == "INV-0001"  # type: ignore[union-attr]
    assert _find(root, "cbc:InvoiceTypeCode").text == "380"  # type: ignore[union-attr]
    assert _find(root, "cbc:DocumentCurrencyCode").text == "EUR"  # type: ignore[union-attr]


def test_output_is_utf8_bytes() -> None:
    result = generate_ubl(SAMPLE_INVOICE)
    assert isinstance(result, bytes)
    assert b"utf-8" in result[:100].lower()


# --- BuyerReference ---


def test_buyer_reference_from_field() -> None:
    inv = {**SAMPLE_INVOICE, "buyer_reference": "PO-2025-042"}
    root = _parse(inv)
    ref = _find(root, "cbc:BuyerReference")
    assert ref is not None
    assert ref.text == "PO-2025-042"


def test_buyer_reference_defaults_to_invoice_number() -> None:
    root = _parse(SAMPLE_INVOICE)
    ref = _find(root, "cbc:BuyerReference")
    assert ref is not None
    assert ref.text == "INV-TEST-001"


# --- Fractional tax rates ---


def test_fractional_tax_percent() -> None:
    inv = {
        **SAMPLE_INVOICE,
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.00, "tax_category": "S", "tax_percent": 7.7}],
    }
    root = _parse(inv)
    # TaxCategory Percent in TaxSubtotal
    subtotal = root.find(f".//{{{CAC}}}TaxSubtotal")
    assert subtotal is not None
    pct = subtotal.find(f".//{{{CAC}}}TaxCategory/{{{CBC}}}Percent")
    assert pct is not None
    assert pct.text == "7.7"

    # ClassifiedTaxCategory Percent on line item
    ctc = root.find(f".//{{{CAC}}}InvoiceLine//{{{CAC}}}ClassifiedTaxCategory/{{{CBC}}}Percent")
    assert ctc is not None
    assert ctc.text == "7.7"


# --- Decimal precision ---


def test_decimal_precision_no_float_drift() -> None:
    """Three items at 33.33 each should total 99.99, not suffer float drift."""
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {"id": str(i), "quantity": 1, "unit_price": 33.33, "tax_category": "E", "tax_percent": 0}
            for i in range(1, 4)
        ],
    }
    root = _parse(inv)
    lmt = root.find(f".//{{{CAC}}}LegalMonetaryTotal")
    assert lmt is not None
    assert lmt.find(f"{{{CBC}}}LineExtensionAmount").text == "99.99"  # type: ignore[union-attr]
    assert lmt.find(f"{{{CBC}}}PayableAmount").text == "99.99"  # type: ignore[union-attr]
