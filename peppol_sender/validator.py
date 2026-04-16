"""Validator for UBL invoices and credit notes.

Provides basic structural checks (required element presence) and XSD validation
against the official UBL 2.1 schemas. Both the required-element list and the
XSD schema are selected from the XML root element, so callers pass raw XML
bytes and the validator dispatches on document type internally.

Each check returns a list of rule dicts:
{ 'id': str, 'type': 'FATAL'|'WARNING', 'location': str, 'message': str }
"""

import functools
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import xmlschema

_CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas" / "xsd" / "maindoc"
_SCHEMA_FILES = {
    "Invoice": _SCHEMAS_DIR / "UBL-Invoice-2.1.xsd",
    "CreditNote": _SCHEMAS_DIR / "UBL-CreditNote-2.1.xsd",
}

_CREDIT_TRANSFER_CODES = {"30", "58"}

# PEPPOL-EN16931-F001: date elements must be formatted YYYY-MM-DD.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_ELEMENTS = ("IssueDate", "DueDate", "TaxPointDate", "StartDate", "EndDate", "ActualDeliveryDate")

# Required elements shared between Invoice and CreditNote. Keyed by the local
# tag name (without namespace) for readable error IDs; paired with a
# human-readable description.
_SHARED_REQUIRED: list[tuple[str, str, str]] = [
    (_CBC_NS, "CustomizationID", "CustomizationID"),
    (_CBC_NS, "ProfileID", "ProfileID"),
    (_CBC_NS, "ID", "Document ID"),
    (_CBC_NS, "IssueDate", "IssueDate"),
    (_CBC_NS, "DocumentCurrencyCode", "DocumentCurrencyCode"),
    (_CAC_NS, "AccountingSupplierParty", "Seller"),
    (_CAC_NS, "AccountingCustomerParty", "Buyer"),
    (_CAC_NS, "TaxTotal", "TaxTotal"),
    (_CAC_NS, "LegalMonetaryTotal", "LegalMonetaryTotal"),
]


def _required_for(root_tag: str) -> list[tuple[str, str, str]]:
    """Return the required-element list for a given document root tag.

    Invoice and CreditNote share almost everything; only the type-code
    element and the line wrapper differ.
    """
    if root_tag == "Invoice":
        return [
            *_SHARED_REQUIRED,
            (_CBC_NS, "InvoiceTypeCode", "InvoiceTypeCode"),
            (_CAC_NS, "InvoiceLine", "Invoice lines"),
        ]
    if root_tag == "CreditNote":
        return [
            *_SHARED_REQUIRED,
            (_CBC_NS, "CreditNoteTypeCode", "CreditNoteTypeCode"),
            (_CAC_NS, "CreditNoteLine", "Credit note lines"),
        ]
    raise ValueError(f"Unknown root tag: {root_tag!r}")


def _root_tag(root: ET.Element) -> str:
    """Return the local name of an XML root element (namespace stripped)."""
    return root.tag.rsplit("}", 1)[-1]


def validate_basic(xml_bytes: bytes) -> list[dict]:
    """Run basic structural checks and return validation rules.

    Dispatches on the XML root element: `<Invoice>` and `<CreditNote>` are
    both accepted, with the appropriate required-element list. Unknown roots
    are rejected with a single LOCAL-UNKNOWN-ROOT FATAL rule. Also applies
    BR-50 (IBAN required on credit transfers) and the F001 date format check.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [{"id": "LOCAL-XML-PARSE", "type": "FATAL", "location": "/", "message": f"XML parse error: {e}"}]

    root_tag = _root_tag(root)
    if root_tag not in _SCHEMA_FILES:
        return [
            {
                "id": "LOCAL-UNKNOWN-ROOT",
                "type": "FATAL",
                "location": f"/*:{root_tag}",
                "message": (f"Unknown document root element {root_tag!r}: expected 'Invoice' or 'CreditNote'."),
            }
        ]

    rules: list[dict] = []
    for ns, tag_name, desc in _required_for(root_tag):
        full_tag = f"{{{ns}}}{tag_name}"
        if root.find(f".//{full_tag}") is None:
            rules.append(
                {
                    "id": f"LOCAL-MISSING-{tag_name}",
                    "type": "FATAL",
                    "location": f"/*:{root_tag}/*:{tag_name}",
                    "message": f"Missing required element: {desc} ({tag_name})",
                }
            )

    rules.extend(_check_br50(root, root_tag))
    rules.extend(_check_date_formats(root))
    return rules


def _check_date_formats(root: ET.Element) -> list[dict]:
    """Local mirror of PEPPOL-EN16931-F001: every date element MUST be YYYY-MM-DD.

    Catches empty or malformed dates before transmission so they don't surface
    as F001 after a failed send.
    """
    rules: list[dict] = []
    for el in root.iter():
        name = el.tag.rsplit("}", 1)[-1]
        if name not in _DATE_ELEMENTS:
            continue
        text = (el.text or "").strip()
        if _ISO_DATE_RE.fullmatch(text):
            continue
        rules.append(
            {
                "id": "LOCAL-F001",
                "type": "FATAL",
                "location": f"/*:{name}",
                "message": f"F001: {name} must be formatted YYYY-MM-DD (got {text!r}).",
            }
        )
    return rules


def _check_br50(root: ET.Element, root_tag: str) -> list[dict]:
    """BR-50: PayeeFinancialAccount/ID (IBAN) is required when PaymentMeansCode
    is 30 or 58 (credit transfer). Not triggered when PaymentMeans is absent or
    when a non-credit-transfer code is used.
    """
    code_el = root.find(f".//{{{_CBC_NS}}}PaymentMeansCode")
    if code_el is None or (code_el.text or "").strip() not in _CREDIT_TRANSFER_CODES:
        return []

    iban_el = root.find(f".//{{{_CAC_NS}}}PaymentMeans/{{{_CAC_NS}}}PayeeFinancialAccount/{{{_CBC_NS}}}ID")
    if iban_el is not None and (iban_el.text or "").strip():
        return []

    return [
        {
            "id": "LOCAL-BR-50",
            "type": "FATAL",
            "location": f"/*:{root_tag}/*:PaymentMeans/*:PayeeFinancialAccount/*:ID",
            "message": (
                "BR-50: PayeeFinancialAccount/ID (IBAN) is required when "
                "PaymentMeansCode is 30 or 58 (credit transfer)."
            ),
        }
    ]


@functools.cache
def _schema_for(root_tag: str) -> xmlschema.XMLSchema:
    """Load the UBL 2.1 XSD schema matching the given document root tag.

    Cached so each schema file is parsed at most once per process.
    """
    return xmlschema.XMLSchema(str(_SCHEMA_FILES[root_tag]))


def validate_xsd(xml_bytes: bytes) -> list[dict]:
    """Validate XML against the UBL 2.1 XSD schema matching its document type.

    Picks `UBL-Invoice-2.1.xsd` for `<Invoice>` roots and
    `UBL-CreditNote-2.1.xsd` for `<CreditNote>` roots. Unknown roots are
    reported by `validate_basic()` first; this function's `LOCAL-UNKNOWN-ROOT`
    fallback is a safety net for callers that bypass `validate_basic`.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [{"id": "LOCAL-XML-PARSE", "type": "FATAL", "location": "/", "message": f"XML parse error: {e}"}]

    root_tag = _root_tag(root)
    if root_tag not in _SCHEMA_FILES:
        return [
            {
                "id": "LOCAL-UNKNOWN-ROOT",
                "type": "FATAL",
                "location": f"/*:{root_tag}",
                "message": f"Unknown document root element {root_tag!r}: expected 'Invoice' or 'CreditNote'.",
            }
        ]

    try:
        schema = _schema_for(root_tag)
    except Exception as e:
        return [
            {
                "id": "LOCAL-XSD-LOAD",
                "type": "FATAL",
                "location": "/",
                "message": f"Failed to load XSD schema: {e}",
            }
        ]

    rules: list[dict] = []
    for err in schema.iter_errors(xml_bytes):
        rules.append(
            {
                "id": "XSD-VALIDATION",
                "type": "FATAL",
                "location": err.path or "/",
                "message": err.reason or str(err),
            }
        )

    return rules
