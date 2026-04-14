"""Validator for UBL invoices.

Provides basic structural checks (required element presence) and XSD validation
against the official UBL 2.1 schema. Each check returns a list of rule dicts:
{ 'id': str, 'type': 'FATAL'|'WARNING', 'location': str, 'message': str }
"""

import functools
from pathlib import Path
from xml.etree import ElementTree as ET

import xmlschema

_UBL_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "xsd" / "maindoc" / "UBL-Invoice-2.1.xsd"

# Required elements and their search paths
_REQUIRED = [
    (f"{{{_CBC_NS}}}CustomizationID", "CustomizationID"),
    (f"{{{_CBC_NS}}}ProfileID", "ProfileID"),
    (f"{{{_CBC_NS}}}ID", "Invoice ID"),
    (f"{{{_CBC_NS}}}IssueDate", "IssueDate"),
    (f"{{{_CBC_NS}}}InvoiceTypeCode", "InvoiceTypeCode"),
    (f"{{{_CBC_NS}}}DocumentCurrencyCode", "DocumentCurrencyCode"),
    (f"{{{_CAC_NS}}}AccountingSupplierParty", "Seller"),
    (f"{{{_CAC_NS}}}AccountingCustomerParty", "Buyer"),
    (f"{{{_CAC_NS}}}TaxTotal", "TaxTotal"),
    (f"{{{_CAC_NS}}}LegalMonetaryTotal", "LegalMonetaryTotal"),
    (f"{{{_CAC_NS}}}InvoiceLine", "Invoice lines"),
]


def validate_basic(xml_bytes: bytes) -> list[dict]:
    """Run basic structural checks and return validation rules.

    Checks for presence of required EN-16931 elements.
    """
    rules: list[dict] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [{"id": "LOCAL-XML-PARSE", "type": "FATAL", "location": "/", "message": f"XML parse error: {e}"}]

    for full_tag, desc in _REQUIRED:
        tag_name = full_tag.split("}")[-1]
        if root.find(f".//{full_tag}") is None:
            rules.append(
                {
                    "id": f"LOCAL-MISSING-{tag_name}",
                    "type": "FATAL",
                    "location": f"/*:Invoice/*:{tag_name}",
                    "message": f"Missing required element: {desc} ({tag_name})",
                }
            )

    return rules


@functools.cache
def _get_schema() -> xmlschema.XMLSchema:
    """Load the UBL 2.1 XSD schema once and cache it."""
    return xmlschema.XMLSchema(str(_SCHEMA_PATH))


def validate_xsd(xml_bytes: bytes) -> list[dict]:
    """Validate XML against the UBL 2.1 XSD schema.

    Returns a list of FATAL rule dicts for each validation error.
    """
    rules: list[dict] = []
    try:
        schema = _get_schema()
    except Exception as e:
        return [
            {
                "id": "LOCAL-XSD-LOAD",
                "type": "FATAL",
                "location": "/",
                "message": f"Failed to load XSD schema: {e}",
            }
        ]

    errors = list(schema.iter_errors(xml_bytes))
    for err in errors:
        rules.append(
            {
                "id": "XSD-VALIDATION",
                "type": "FATAL",
                "location": err.path or "/",
                "message": err.reason or str(err),
            }
        )

    return rules
