"""Tests for peppol_sender.ubl — UBL 2.1 invoice generation."""

from pathlib import Path
from xml.etree import ElementTree as ET

from peppol_sender.ubl import generate_credit_note, generate_ubl

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

_FIXTURES = Path(__file__).parent / "fixtures"


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


def test_line_service_date_single_day() -> None:
    """A single `service_date` produces InvoicePeriod with equal Start/End."""
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {
                "id": "1",
                "description": "Consulting",
                "quantity": 1,
                "unit_price": 100.0,
                "tax_category": "E",
                "tax_percent": 0,
                "service_date": "2026-04-10",
            },
        ],
    }
    root = _parse(inv)
    period = root.find(f".//{{{CAC}}}InvoiceLine/{{{CAC}}}InvoicePeriod")
    assert period is not None
    assert period.find(f"{{{CBC}}}StartDate").text == "2026-04-10"  # type: ignore[union-attr]
    assert period.find(f"{{{CBC}}}EndDate").text == "2026-04-10"  # type: ignore[union-attr]


def test_line_service_date_range() -> None:
    """Separate start/end dates produce InvoicePeriod with distinct values."""
    inv = {
        **SAMPLE_INVOICE,
        "lines": [
            {
                "id": "1",
                "description": "Consulting",
                "quantity": 1,
                "unit_price": 100.0,
                "tax_category": "E",
                "tax_percent": 0,
                "service_start_date": "2026-04-01",
                "service_end_date": "2026-04-10",
            },
        ],
    }
    root = _parse(inv)
    period = root.find(f".//{{{CAC}}}InvoiceLine/{{{CAC}}}InvoicePeriod")
    assert period is not None
    assert period.find(f"{{{CBC}}}StartDate").text == "2026-04-01"  # type: ignore[union-attr]
    assert period.find(f"{{{CBC}}}EndDate").text == "2026-04-10"  # type: ignore[union-attr]


def test_line_no_service_date_omits_invoice_period() -> None:
    root = _parse(SAMPLE_INVOICE)
    assert root.find(f".//{{{CAC}}}InvoiceLine/{{{CAC}}}InvoicePeriod") is None


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


# --- Payment means (BR-50 structured credit-transfer block) ---


PAYMENT_MEANS_SAMPLE = {
    "code": "30",
    "iban": "BE68539007547034",
    "bic": "BBRUBEBB",
    "account_name": "Test Seller BV",
    "payment_id": "INV-TEST-001",
}


def _with_pm(**overrides: object) -> dict:
    """SAMPLE_INVOICE augmented with a payment_means block."""
    pm = {**PAYMENT_MEANS_SAMPLE, **overrides}
    return {**SAMPLE_INVOICE, "payment_means": pm}


def test_payment_means_structure() -> None:
    root = _parse(_with_pm())
    pms = root.findall(f"{{{CAC}}}PaymentMeans")
    assert len(pms) == 1
    pm = pms[0]
    assert pm.find(f"{{{CBC}}}PaymentMeansCode").text == "30"  # type: ignore[union-attr]
    assert pm.find(f"{{{CBC}}}PaymentID").text == "INV-TEST-001"  # type: ignore[union-attr]
    account = pm.find(f"{{{CAC}}}PayeeFinancialAccount")
    assert account is not None
    assert account.find(f"{{{CBC}}}ID").text == "BE68539007547034"  # type: ignore[union-attr]
    assert account.find(f"{{{CBC}}}Name").text == "Test Seller BV"  # type: ignore[union-attr]
    branch = account.find(f"{{{CAC}}}FinancialInstitutionBranch")
    assert branch is not None
    assert branch.find(f"{{{CBC}}}ID").text == "BBRUBEBB"  # type: ignore[union-attr]


def test_payment_means_bic_optional() -> None:
    pm = {k: v for k, v in PAYMENT_MEANS_SAMPLE.items() if k != "bic"}
    root = _parse({**SAMPLE_INVOICE, "payment_means": pm})
    account = root.find(f".//{{{CAC}}}PayeeFinancialAccount")
    assert account is not None
    assert account.find(f"{{{CAC}}}FinancialInstitutionBranch") is None


def test_payment_means_payment_id_defaults_to_invoice_number() -> None:
    pm = {k: v for k, v in PAYMENT_MEANS_SAMPLE.items() if k != "payment_id"}
    root = _parse({**SAMPLE_INVOICE, "payment_means": pm})
    pid = root.find(f".//{{{CAC}}}PaymentMeans/{{{CBC}}}PaymentID")
    assert pid is not None
    assert pid.text == SAMPLE_INVOICE["invoice_number"]


def test_payment_means_account_name_defaults_to_seller_name() -> None:
    pm = {k: v for k, v in PAYMENT_MEANS_SAMPLE.items() if k != "account_name"}
    root = _parse({**SAMPLE_INVOICE, "payment_means": pm})
    name = root.find(f".//{{{CAC}}}PayeeFinancialAccount/{{{CBC}}}Name")
    assert name is not None
    assert name.text == SAMPLE_INVOICE["seller"]["name"]  # type: ignore[index]


def test_payment_means_absent_when_omitted() -> None:
    root = _parse(SAMPLE_INVOICE)
    assert root.find(f"{{{CAC}}}PaymentMeans") is None


def test_payment_means_emits_with_missing_iban() -> None:
    """Partial payment_means (no IBAN) still emits PaymentMeansCode so BR-50 can fire."""
    pm = {"code": "30"}
    root = _parse({**SAMPLE_INVOICE, "payment_means": pm})
    pm_el = root.find(f"{{{CAC}}}PaymentMeans")
    assert pm_el is not None
    assert pm_el.find(f"{{{CBC}}}PaymentMeansCode").text == "30"  # type: ignore[union-attr]
    assert pm_el.find(f"{{{CAC}}}PayeeFinancialAccount") is None


def test_payment_means_before_payment_terms() -> None:
    """UBL xs:sequence: PaymentMeans must precede PaymentTerms."""
    root = _parse(_with_pm())
    children = list(root)
    tags = [c.tag.split("}")[-1] for c in children]
    pm_idx = tags.index("PaymentMeans")
    pt_idx = tags.index("PaymentTerms")
    cust_idx = tags.index("AccountingCustomerParty")
    assert cust_idx < pm_idx < pt_idx


# --- Embedded PDF visual representation (R008) ---


def test_embed_pdf_false_is_default() -> None:
    root = _parse(SAMPLE_INVOICE)
    assert root.find(f"{{{CAC}}}AdditionalDocumentReference") is None


def test_embed_pdf_true_emits_additional_document_reference() -> None:
    xml = generate_ubl(SAMPLE_INVOICE, embed_pdf=True)
    root = ET.fromstring(xml)
    adrs = root.findall(f"{{{CAC}}}AdditionalDocumentReference")
    assert len(adrs) == 1
    adr = adrs[0]
    assert adr.find(f"{{{CBC}}}ID").text == "INV-TEST-001"  # type: ignore[union-attr]
    assert adr.find(f"{{{CBC}}}DocumentDescription").text == "Commercial Invoice"  # type: ignore[union-attr]
    attachment = adr.find(f"{{{CAC}}}Attachment")
    assert attachment is not None
    blob = attachment.find(f"{{{CBC}}}EmbeddedDocumentBinaryObject")
    assert blob is not None
    assert blob.get("mimeCode") == "application/pdf"
    assert blob.get("filename") == "INV-TEST-001.pdf"
    # Decode base64 and confirm it is a real PDF
    import base64

    assert blob.text is not None
    decoded = base64.b64decode(blob.text)
    assert decoded.startswith(b"%PDF-")


def test_embed_pdf_position_in_xs_sequence() -> None:
    """AdditionalDocumentReference MUST sit between BuyerReference and AccountingSupplierParty."""
    xml = generate_ubl(SAMPLE_INVOICE, embed_pdf=True)
    root = ET.fromstring(xml)
    tags = [c.tag.split("}")[-1] for c in root]
    br_idx = tags.index("BuyerReference")
    adr_idx = tags.index("AdditionalDocumentReference")
    sup_idx = tags.index("AccountingSupplierParty")
    assert br_idx < adr_idx < sup_idx


def test_embed_pdf_passes_xsd() -> None:
    """The embed path must produce XML that still passes UBL 2.1 XSD validation."""
    from peppol_sender.validator import validate_xsd

    xml = generate_ubl(SAMPLE_INVOICE, embed_pdf=True)
    rules = validate_xsd(xml)
    assert rules == []


def test_generate_ubl_output_byte_identical_to_reference() -> None:
    # Regression guard for the shared line/document refactor. The reference
    # file was captured from the pre-refactor generate_ubl(SAMPLE_INVOICE)
    # output. Any drift in element ordering, attribute serialisation, or
    # whitespace will fail this test. Do not regenerate casually.
    expected = (_FIXTURES / "reference_invoice.xml").read_bytes()
    actual = generate_ubl(SAMPLE_INVOICE)
    assert actual == expected


# --- Credit note generation ---


# Mirror SAMPLE_INVOICE with credit-note-specific fields. The billing_reference
# block is included by default so the common case (credit note referencing the
# invoice it corrects) is exercised by every credit-note test that uses this
# fixture. No due_date — CreditNote schema does not allow it.
SAMPLE_CREDIT_NOTE = {
    "invoice_number": "CN-TEST-001",
    "issue_date": "2025-02-01",
    "credit_note_type_code": "381",
    "currency": "EUR",
    "payment_terms": "Refund within 14 days",
    "billing_reference": {
        "id": "INV-TEST-001",
        "issue_date": "2025-01-15",
    },
    "seller": SAMPLE_INVOICE["seller"],
    "buyer": SAMPLE_INVOICE["buyer"],
    "lines": [
        {
            "id": "1",
            "description": "Refund for consulting (hours cancelled)",
            "quantity": 2,
            "unit": "HUR",
            "unit_price": 150.00,
            "tax_category": "E",
            "tax_percent": 0,
        }
    ],
}


def _parse_cn(data: dict) -> ET.Element:
    return ET.fromstring(generate_credit_note(data))


def test_credit_note_root_element() -> None:
    root = _parse_cn(SAMPLE_CREDIT_NOTE)
    assert root.tag.rsplit("}", 1)[-1] == "CreditNote"
    assert root.tag.startswith("{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}")


def test_credit_note_type_code_default() -> None:
    data = {**SAMPLE_CREDIT_NOTE}
    del data["credit_note_type_code"]
    root = _parse_cn(data)
    type_code = _find(root, "cbc:CreditNoteTypeCode")
    assert type_code is not None
    assert type_code.text == "381"


def test_credit_note_type_code_override() -> None:
    data = {**SAMPLE_CREDIT_NOTE, "credit_note_type_code": "384"}
    root = _parse_cn(data)
    type_code = _find(root, "cbc:CreditNoteTypeCode")
    assert type_code is not None
    assert type_code.text == "384"


def test_credit_note_lines_use_correct_wrapper() -> None:
    root = _parse_cn(SAMPLE_CREDIT_NOTE)
    # The line wrapper lives in the cac: namespace, not the default.
    lines = root.findall(f"{{{CAC}}}CreditNoteLine")
    assert len(lines) == 1
    qty = lines[0].find(f"{{{CBC}}}CreditedQuantity")
    assert qty is not None
    assert qty.text == "2"
    assert qty.get("unitCode") == "HUR"
    # The invoice-specific element name MUST NOT leak into credit notes.
    assert root.find(f".//{{{CAC}}}InvoiceLine") is None
    assert root.find(f".//{{{CBC}}}InvoicedQuantity") is None


def test_credit_note_header_shape() -> None:
    root = _parse_cn(SAMPLE_CREDIT_NOTE)
    for tag in [
        "CustomizationID",
        "ProfileID",
        "ID",
        "IssueDate",
        "CreditNoteTypeCode",
        "DocumentCurrencyCode",
    ]:
        assert _find(root, f"cbc:{tag}") is not None, f"Missing: {tag}"
    # CreditNote schema does not have DueDate — must be absent even if the
    # caller accidentally supplies it.
    data = {**SAMPLE_CREDIT_NOTE, "due_date": "2025-03-01"}
    root_with_due = _parse_cn(data)
    assert _find(root_with_due, "cbc:DueDate") is None


def test_credit_note_shared_subtrees_match_invoice() -> None:
    # Serialise an invoice and a credit note from equivalent dicts, with
    # billing_reference absent on BOTH so we isolate the shared subtrees
    # (BillingReference is structurally valid on both document types, but
    # comparing with it present would just complicate the diff).
    invoice_data = {k: v for k, v in SAMPLE_INVOICE.items()}
    cn_data = {k: v for k, v in SAMPLE_CREDIT_NOTE.items() if k not in ("credit_note_type_code", "billing_reference")}
    # Give the credit note an invoice_type_code default so field naming
    # differences don't introduce stray content — the generator only reads
    # the key that matches its document type.
    inv_root = ET.fromstring(generate_ubl(invoice_data))
    cn_root = _parse_cn(cn_data)

    def _canonical(el: ET.Element) -> bytes:
        return ET.tostring(el, encoding="utf-8")  # type: ignore[no-any-return]

    for tag in [
        "AccountingSupplierParty",
        "AccountingCustomerParty",
        "TaxTotal",
        "LegalMonetaryTotal",
    ]:
        inv_sub = inv_root.find(f"{{{CAC}}}{tag}")
        cn_sub = cn_root.find(f"{{{CAC}}}{tag}")
        assert inv_sub is not None and cn_sub is not None, tag
        assert _canonical(inv_sub) == _canonical(cn_sub), f"Subtree {tag} differs between invoice and credit note"


def test_credit_note_passes_credit_note_xsd() -> None:
    from peppol_sender.validator import validate_xsd

    rules = validate_xsd(generate_credit_note(SAMPLE_CREDIT_NOTE))
    assert rules == []


# --- BillingReference (BT-25/BT-26) ---


def test_billing_reference_emitted_when_present() -> None:
    root = _parse_cn(SAMPLE_CREDIT_NOTE)
    idr = root.find(f"{{{CAC}}}BillingReference/{{{CAC}}}InvoiceDocumentReference")
    assert idr is not None
    assert idr.find(f"{{{CBC}}}ID").text == "INV-TEST-001"  # type: ignore[union-attr]
    assert idr.find(f"{{{CBC}}}IssueDate").text == "2025-01-15"  # type: ignore[union-attr]


def test_billing_reference_omitted_when_absent() -> None:
    data = {k: v for k, v in SAMPLE_CREDIT_NOTE.items() if k != "billing_reference"}
    root = _parse_cn(data)
    assert root.find(f".//{{{CAC}}}BillingReference") is None
    # And the same for invoices — byte-identity test already proves this, but
    # covering it explicitly makes the regression surface in one obvious test.
    inv_root = ET.fromstring(generate_ubl(SAMPLE_INVOICE))
    assert inv_root.find(f".//{{{CAC}}}BillingReference") is None


def test_billing_reference_on_invoice_also_supported() -> None:
    # Corrective-invoice series use case: an Invoice can reference a
    # preceding invoice. Helper is document-type agnostic.
    data = {
        **SAMPLE_INVOICE,
        "billing_reference": {"id": "INV-PREV-99", "issue_date": "2024-12-31"},
    }
    root = ET.fromstring(generate_ubl(data))
    idr = root.find(f"{{{CAC}}}BillingReference/{{{CAC}}}InvoiceDocumentReference")
    assert idr is not None
    assert idr.find(f"{{{CBC}}}ID").text == "INV-PREV-99"  # type: ignore[union-attr]
    assert idr.find(f"{{{CBC}}}IssueDate").text == "2024-12-31"  # type: ignore[union-attr]


def test_billing_reference_precedes_parties() -> None:
    # UBL xs:sequence: BillingReference MUST come before AccountingSupplierParty.
    root = _parse_cn(SAMPLE_CREDIT_NOTE)
    tags = [c.tag.rsplit("}", 1)[-1] for c in root]
    assert tags.index("BillingReference") < tags.index("AccountingSupplierParty")
