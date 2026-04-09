"""Minimal validator for generated UBL invoices.

This validator performs lightweight checks (presence of required elements)
and returns a list of validation rule dicts similar to the Peppol report.
Each rule is: { 'id': 'LOCAL-01', 'type': 'FATAL'|'WARNING', 'location': xpath, 'message': str }
"""

from xml.etree import ElementTree as ET

NS = {"ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"}


def _find(root: ET.Element, tag: str) -> ET.Element | None:
    return root.find(f".//{{{NS['ubl']}}}{tag}")


def validate_basic(xml_bytes: bytes) -> list[dict]:
    """Run basic structural checks and return validation rules.

    This is not a replacement for XSD/Schematron validation; it helps catch
    obvious omissions before attempting to send.
    """
    rules = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [{"id": "LOCAL-XML-PARSE", "type": "FATAL", "location": "/", "message": f"XML parse error: {e}"}]

    # required elements
    required = [
        ("ID", "Invoice ID"),
        ("IssueDate", "IssueDate"),
        ("AccountingSupplierParty", "Seller"),
        ("AccountingCustomerParty", "Buyer"),
        ("InvoiceLine", "Invoice lines"),
    ]

    for tag, desc in required:
        el = _find(root, tag)
        if el is None:
            rules.append(
                {
                    "id": f"LOCAL-MISSING-{tag}",
                    "type": "FATAL",
                    "location": f"/*:Invoice/*:{tag}",
                    "message": f"Missing required element: {desc} ({tag})",
                }
            )

    return rules
