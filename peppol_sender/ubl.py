"""UBL 2.1 invoice generator (EN-16931 compliant).

Generates PEPPOL BIS Billing 3.0 compliant UBL 2.1 Invoice XML from a JSON-like
invoice data structure. Supports VAT-exempt businesses (tax category E/O).
"""

import base64
from collections import defaultdict
from datetime import date
from decimal import Decimal
from xml.dom import minidom
from xml.etree import ElementTree as ET

_NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

_CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
_PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


def _tag(ns: str, tag: str) -> str:
    return f"{{{_NS[ns]}}}{tag}"


def _sub(parent: ET.Element, ns: str, tag: str, text: str | None = None, **attribs: str) -> ET.Element:
    """Add a sub-element with optional text and attributes."""
    el = ET.SubElement(parent, _tag(ns, tag))
    if text is not None:
        el.text = text
    for k, v in attribs.items():
        el.set(k, v)
    return el


def _add_party(inv: ET.Element, wrapper_tag: str, party: dict, currency: str) -> None:
    """Add an AccountingSupplierParty/AccountingCustomerParty subtree."""
    wrapper = _sub(inv, "cac", wrapper_tag)
    p = _sub(wrapper, "cac", "Party")

    # EndpointID
    endpoint_id = party.get("endpoint_id", "")
    endpoint_scheme = party.get("endpoint_scheme", "0208")
    _sub(p, "cbc", "EndpointID", endpoint_id, schemeID=endpoint_scheme)

    # PartyName
    name_el = _sub(p, "cac", "PartyName")
    _sub(name_el, "cbc", "Name", party.get("name", ""))

    # PostalAddress
    addr = _sub(p, "cac", "PostalAddress")
    if party.get("street"):
        _sub(addr, "cbc", "StreetName", party["street"])
    if party.get("city"):
        _sub(addr, "cbc", "CityName", party["city"])
    if party.get("postal_code"):
        _sub(addr, "cbc", "PostalZone", party["postal_code"])
    country_el = _sub(addr, "cac", "Country")
    _sub(country_el, "cbc", "IdentificationCode", party.get("country", ""))

    # PartyTaxScheme (optional, for parties with VAT number)
    if party.get("vat"):
        pts = _sub(p, "cac", "PartyTaxScheme")
        _sub(pts, "cbc", "CompanyID", party["vat"])
        ts = _sub(pts, "cac", "TaxScheme")
        _sub(ts, "cbc", "ID", "VAT")

    # PartyLegalEntity — RegistrationName + optional CompanyID (BT-30/BT-47)
    ple = _sub(p, "cac", "PartyLegalEntity")
    _sub(ple, "cbc", "RegistrationName", party.get("registration_name", party.get("name", "")))
    legal_id = party.get("legal_id")
    if legal_id:
        scheme = party.get("legal_id_scheme")
        attrs = {"schemeID": scheme} if scheme else {}
        _sub(ple, "cbc", "CompanyID", legal_id, **attrs)

    # Contact — BT-41..43 (seller) / BT-56..58 (buyer). All optional.
    if party.get("contact_name") or party.get("contact_phone") or party.get("contact_email"):
        contact = _sub(p, "cac", "Contact")
        if party.get("contact_name"):
            _sub(contact, "cbc", "Name", party["contact_name"])
        if party.get("contact_phone"):
            _sub(contact, "cbc", "Telephone", party["contact_phone"])
        if party.get("contact_email"):
            _sub(contact, "cbc", "ElectronicMail", party["contact_email"])


def _dec(value: object) -> Decimal:
    """Convert a value to Decimal, rounding to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _add_tax_total(inv: ET.Element, lines: list[dict], currency: str) -> Decimal:
    """Add TaxTotal element. Returns the total tax amount."""
    groups: dict[tuple[str, Decimal], Decimal] = defaultdict(lambda: Decimal("0"))
    for line in lines:
        cat = line.get("tax_category", "E")
        pct = Decimal(str(line.get("tax_percent", 0)))
        ext = _dec(line.get("line_extension_amount", line.get("unit_price", 0) * line.get("quantity", 1)))
        groups[(cat, pct)] += ext

    total_tax = Decimal("0")
    tax_total = _sub(inv, "cac", "TaxTotal")

    # Compute total tax first (need it for TaxAmount which comes before subtotals)
    subtotals = []
    for (cat, pct), taxable in groups.items():
        tax_amt = _dec(taxable * pct / 100)
        total_tax += tax_amt
        subtotals.append((cat, pct, taxable, tax_amt))

    _sub(tax_total, "cbc", "TaxAmount", f"{total_tax:.2f}", currencyID=currency)

    for cat, pct, taxable, tax_amt in subtotals:
        st = _sub(tax_total, "cac", "TaxSubtotal")
        _sub(st, "cbc", "TaxableAmount", f"{taxable:.2f}", currencyID=currency)
        _sub(st, "cbc", "TaxAmount", f"{tax_amt:.2f}", currencyID=currency)
        tc = _sub(st, "cac", "TaxCategory")
        _sub(tc, "cbc", "ID", cat)
        _sub(tc, "cbc", "Percent", f"{pct:g}")
        if cat in ("E", "O") and pct == 0:
            _sub(tc, "cbc", "TaxExemptionReason", "Exempt" if cat == "E" else "Not subject to VAT")
        ts = _sub(tc, "cac", "TaxScheme")
        _sub(ts, "cbc", "ID", "VAT")

    return total_tax


def _add_additional_document_reference(
    inv: ET.Element,
    pdf_bytes: bytes,
    document_id: str,
    description: str = "Commercial Invoice",
) -> None:
    """Embed a visual representation (PDF) as cac:AdditionalDocumentReference.

    PEPPOL BIS Billing 3.0 rule R008 allows exactly one visual per invoice,
    restricted to a short list of MIME types. We emit application/pdf.
    """
    adr = _sub(inv, "cac", "AdditionalDocumentReference")
    _sub(adr, "cbc", "ID", document_id)
    _sub(adr, "cbc", "DocumentDescription", description)
    attachment = _sub(adr, "cac", "Attachment")
    _sub(
        attachment,
        "cbc",
        "EmbeddedDocumentBinaryObject",
        base64.b64encode(pdf_bytes).decode("ascii"),
        mimeCode="application/pdf",
        filename=f"{document_id}.pdf",
    )


def _add_payment_means(inv: ET.Element, invoice: dict, seller_name: str) -> None:
    """Add cac:PaymentMeans with credit-transfer code and PayeeFinancialAccount.

    Emitted only when the invoice dict contains a `payment_means` block. Default
    `code` is "30" (UNCL4461 credit transfer). `payment_id` defaults to the
    invoice number; `account_name` defaults to the seller name.
    """
    pm_data = invoice.get("payment_means")
    if not pm_data:
        return

    pm = _sub(inv, "cac", "PaymentMeans")
    _sub(pm, "cbc", "PaymentMeansCode", str(pm_data.get("code", "30")))

    payment_id = pm_data.get("payment_id", invoice.get("invoice_number"))
    if payment_id:
        _sub(pm, "cbc", "PaymentID", str(payment_id))

    iban = pm_data.get("iban")
    if iban:
        account = _sub(pm, "cac", "PayeeFinancialAccount")
        _sub(account, "cbc", "ID", iban)
        account_name = pm_data.get("account_name", seller_name)
        if account_name:
            _sub(account, "cbc", "Name", account_name)
        bic = pm_data.get("bic")
        if bic:
            branch = _sub(account, "cac", "FinancialInstitutionBranch")
            _sub(branch, "cbc", "ID", bic)


def _add_legal_monetary_total(inv: ET.Element, line_sum: Decimal, tax_total: Decimal, currency: str) -> None:
    """Add LegalMonetaryTotal element."""
    lmt = _sub(inv, "cac", "LegalMonetaryTotal")
    _sub(lmt, "cbc", "LineExtensionAmount", f"{line_sum:.2f}", currencyID=currency)
    _sub(lmt, "cbc", "TaxExclusiveAmount", f"{line_sum:.2f}", currencyID=currency)
    _sub(lmt, "cbc", "TaxInclusiveAmount", f"{line_sum + tax_total:.2f}", currencyID=currency)
    _sub(lmt, "cbc", "PayableAmount", f"{line_sum + tax_total:.2f}", currencyID=currency)


def _add_invoice_line(inv: ET.Element, line: dict, currency: str) -> Decimal:
    """Add a single InvoiceLine element. Returns the line extension amount."""
    il = _sub(inv, "cac", "InvoiceLine")
    _sub(il, "cbc", "ID", str(line.get("id", "1")))

    qty = line.get("quantity", 1)
    unit = line.get("unit", "EA")
    _sub(il, "cbc", "InvoicedQuantity", str(qty), unitCode=unit)

    ext_amt = _dec(line.get("line_extension_amount", line.get("unit_price", 0) * qty))
    _sub(il, "cbc", "LineExtensionAmount", f"{ext_amt:.2f}", currencyID=currency)

    # InvoicePeriod — BG-26 / BT-134..135. Single date supported via service_date;
    # a range via service_start_date / service_end_date. BR-CO-25 requires both
    # start and end to be present when either is, so we mirror if only one is set.
    start_date = line.get("service_start_date") or line.get("service_date")
    end_date = line.get("service_end_date") or line.get("service_date")
    if start_date or end_date:
        period = _sub(il, "cac", "InvoicePeriod")
        _sub(period, "cbc", "StartDate", start_date or end_date)
        _sub(period, "cbc", "EndDate", end_date or start_date)

    # Item
    item = _sub(il, "cac", "Item")
    _sub(item, "cbc", "Name", line.get("description", ""))
    ctc = _sub(item, "cac", "ClassifiedTaxCategory")
    _sub(ctc, "cbc", "ID", line.get("tax_category", "E"))
    pct = Decimal(str(line.get("tax_percent", 0)))
    _sub(ctc, "cbc", "Percent", f"{pct:g}")
    ts = _sub(ctc, "cac", "TaxScheme")
    _sub(ts, "cbc", "ID", "VAT")

    # Price
    price = _sub(il, "cac", "Price")
    _sub(price, "cbc", "PriceAmount", f"{_dec(line.get('unit_price', 0)):.2f}", currencyID=currency)

    return ext_amt


def generate_ubl(invoice: dict, *, embed_pdf: bool = False) -> bytes:
    """Generate an EN-16931 compliant UBL 2.1 Invoice XML.

    invoice: dict with keys: invoice_number, issue_date, due_date, currency,
             invoice_type_code, payment_terms, payment_means, seller, buyer, lines
    embed_pdf: when True, render the invoice as a PDF and embed it as a
               cac:AdditionalDocumentReference (PEPPOL BIS Billing 3.0 R008
               visual representation). Defaults to False so existing callers
               and the test suite remain fast and byte-stable; CLI and webapp
               call sites pass True explicitly.
    Returns: bytes (UTF-8)
    """
    for prefix, uri in _NS.items():
        ET.register_namespace(prefix, uri)

    inv = ET.Element(_tag("", "Invoice"))
    currency = invoice.get("currency", "EUR")

    # Document header (order matters for XSD compliance)
    _sub(inv, "cbc", "CustomizationID", _CUSTOMIZATION_ID)
    _sub(inv, "cbc", "ProfileID", _PROFILE_ID)
    _sub(inv, "cbc", "ID", str(invoice.get("invoice_number", "INV-0001")))
    _sub(inv, "cbc", "IssueDate", invoice.get("issue_date", date.today().isoformat()))
    if invoice.get("due_date"):
        _sub(inv, "cbc", "DueDate", invoice["due_date"])
    _sub(inv, "cbc", "InvoiceTypeCode", str(invoice.get("invoice_type_code", "380")))
    _sub(inv, "cbc", "DocumentCurrencyCode", currency)
    _sub(inv, "cbc", "BuyerReference", str(invoice.get("buyer_reference", invoice.get("invoice_number", "N/A"))))

    # Visual representation — positioned before parties per UBL xs:sequence.
    # Lazy import of render_pdf so that Pango/Cairo are only required when
    # embedding is actually requested.
    if embed_pdf:
        from peppol_sender.pdf import render_pdf

        document_id = str(invoice.get("invoice_number", "INV-0001"))
        _add_additional_document_reference(inv, render_pdf(invoice), document_id)

    # Parties
    _add_party(inv, "AccountingSupplierParty", invoice.get("seller", {}), currency)
    _add_party(inv, "AccountingCustomerParty", invoice.get("buyer", {}), currency)

    # PaymentMeans — must come before PaymentTerms per UBL xs:sequence
    _add_payment_means(inv, invoice, invoice.get("seller", {}).get("name", ""))

    # PaymentTerms
    if invoice.get("payment_terms"):
        pt = _sub(inv, "cac", "PaymentTerms")
        _sub(pt, "cbc", "Note", invoice["payment_terms"])

    # Tax
    lines = invoice.get("lines", [])
    tax_total = _add_tax_total(inv, lines, currency)

    # Totals
    line_sum = Decimal("0")
    for line in lines:
        line_sum += _dec(line.get("line_extension_amount", line.get("unit_price", 0) * line.get("quantity", 1)))
    _add_legal_monetary_total(inv, line_sum, tax_total, currency)

    # Invoice lines
    for line in lines:
        _add_invoice_line(inv, line, currency)

    # Pretty print
    rough = ET.tostring(inv, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ", encoding="utf-8")
