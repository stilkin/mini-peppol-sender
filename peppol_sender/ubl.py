"""UBL invoice generator (minimal)

This module provides a small utility to generate a minimal UBL 2.1 Invoice XML
from a simple JSON-like invoice data structure. The output is bytes (UTF-8).

The generator is intentionally minimal and aimed at producing a valid-looking
UBL invoice for testing with Peppyrus. It does NOT implement the full EN-16931
business rules; use the validator module to run additional checks.
"""
from xml.etree import ElementTree as ET
from xml.dom import minidom

NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
}

def _ns(tag: str) -> str:
    return f"{{{NS['ubl']}}}{tag}"

def generate_ubl(invoice: dict) -> bytes:
    """Generate a minimal UBL 2.1 Invoice XML.

    invoice: dict with keys: invoice_number, issue_date, currency, seller, buyer, lines
    Returns: bytes (UTF-8)
    """
    ET.register_namespace('', NS['ubl'])

    inv = ET.Element(_ns('Invoice'))

    # Basic header
    id_el = ET.SubElement(inv, _ns('ID'))
    id_el.text = str(invoice.get('invoice_number', 'INV-0001'))

    issue = ET.SubElement(inv, _ns('IssueDate'))
    issue.text = invoice.get('issue_date', '')

    # Accounting supplier party (seller)
    supplier = ET.SubElement(inv, _ns('AccountingSupplierParty'))
    party_s = ET.SubElement(supplier, _ns('Party'))
    name_s = ET.SubElement(party_s, _ns('PartyName'))
    n_s = ET.SubElement(name_s, _ns('Name'))
    n_s.text = invoice.get('seller', {}).get('name', 'Seller')

    # Accounting customer party (buyer)
    customer = ET.SubElement(inv, _ns('AccountingCustomerParty'))
    party_c = ET.SubElement(customer, _ns('Party'))
    name_c = ET.SubElement(party_c, _ns('PartyName'))
    n_c = ET.SubElement(name_c, _ns('Name'))
    n_c.text = invoice.get('buyer', {}).get('name', 'Buyer')

    # Invoice lines
    lines = invoice.get('lines', [])
    for line in lines:
        il = ET.SubElement(inv, _ns('InvoiceLine'))
        lid = ET.SubElement(il, _ns('ID'))
        lid.text = str(line.get('id', '1'))

        qty = ET.SubElement(il, _ns('InvoicedQuantity'))
        qty.set('unitCode', line.get('unit', 'EA'))
        qty.text = str(line.get('quantity', 1))

        ext = ET.SubElement(il, _ns('LineExtensionAmount'))
        ext.set('currencyID', invoice.get('currency', 'EUR'))
        ext.text = f"{line.get('line_extension_amount', line.get('unit_price',0)*line.get('quantity',1)):.2f}"

        item = ET.SubElement(il, _ns('Item'))
        item_name = ET.SubElement(item, _ns('Name'))
        item_name.text = line.get('description', '')

        price = ET.SubElement(il, _ns('Price'))
        pamt = ET.SubElement(price, _ns('PriceAmount'))
        pamt.set('currencyID', invoice.get('currency', 'EUR'))
        pamt.text = f"{line.get('unit_price',0):.2f}"

    # Pretty print
    rough = ET.tostring(inv, encoding='utf-8')
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent='  ', encoding='utf-8')
    return pretty
