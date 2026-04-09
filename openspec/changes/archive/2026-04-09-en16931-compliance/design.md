## Context

The UBL generator currently produces a minimal invoice with ~5 elements. A PEPPOL access point will reject it with ~15 FATAL business rule violations (BR-01 through BR-63). The validator only checks basic element presence and has no XSD validation.

The user's company is VAT-exempt (too small), so the tax section must support category E/O with zero rate. Fields requested by the user: addresses, payment terms, due date.

## Goals / Non-Goals

**Goals:**
- Generate EN-16931 compliant UBL 2.1 invoices that pass PEPPOL BIS Billing 3.0 FATAL rules
- Support VAT-exempt businesses (tax category E or O)
- Add XSD validation against official UBL 2.1 schemas
- Update sample_invoice.json with the new required fields
- Update existing tests and add new ones for all new functionality

**Non-Goals:**
- Schematron / EN-16931 business rule validation (deferred)
- Credit notes or other document types (Invoice only)
- Multi-currency support within a single invoice
- Automatic tax calculation from external rate tables

## Decisions

**XSD library: `xmlschema` (pure Python)**
- No C compilation needed — simpler install, no platform-specific build issues.
- Handles the UBL 2.1 multi-file XSD bundle (resolves imports/includes automatically).
- Lighter than `lxml` (~3 MB vs ~15 MB). We don't need lxml's XSLT capabilities.
- Alternative considered: `lxml` — rejected because we don't need its speed or XSLT features, and it adds C build complexity.

**Bundle UBL 2.1 XSD schemas in the repo under `schemas/`**
- Download the official OASIS UBL 2.1 package and keep the `xsd/` subtree.
- Entry point: `schemas/xsd/maindoc/UBL-Invoice-2.1.xsd`.
- The directory structure must stay intact for relative imports between schema files.
- Alternative considered: download at runtime — rejected because it adds network dependency and fragility.

**UBL element ordering**
- UBL XSD enforces a strict element order (it uses `xs:sequence`). The generator must emit elements in the correct order: CustomizationID, ProfileID, ID, IssueDate, DueDate, InvoiceTypeCode, DocumentCurrencyCode, ..., AccountingSupplierParty, AccountingCustomerParty, PaymentTerms, TaxTotal, LegalMonetaryTotal, InvoiceLine.
- This is a critical constraint — getting the order wrong will fail XSD validation.

**Expand `_add_party()` to handle full party details**
- Currently takes only a name string. Extend to accept the full party dict (name, endpoint_id, endpoint_scheme, country, street, city, postal_code, vat, registration_name).
- Add `EndpointID`, `PostalAddress`, `PartyLegalEntity`, and optional `PartyTaxScheme` subtrees.
- The UBL `cac:` (common aggregate) and `cbc:` (common basic) namespaces must be registered in addition to the invoice namespace.

**Additional namespaces needed**
- Current code only uses the UBL Invoice namespace. EN-16931 requires:
  - `cac`: `urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2`
  - `cbc`: `urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2`
- Elements like `cbc:ID`, `cbc:IssueDate`, `cac:Party` must use these namespaces.
- This is a **breaking change** to the XML output — all existing elements will be re-namespaced. Tests must be updated accordingly.

**Tax calculation approach**
- Group line items by `(tax_category, tax_percent)`.
- For each group: sum line extension amounts → taxable amount, apply rate → tax amount.
- Sum all groups for `TaxTotal/TaxAmount`.
- For VAT-exempt (category E/O, percent 0): tax amount is 0.00, include `TaxExemptionReason`.
- `LegalMonetaryTotal` computed from line sums + tax total.

**Updated `sample_invoice.json` schema**
- New top-level fields: `due_date`, `invoice_type_code` (default "380"), `payment_terms`
- New seller/buyer fields: `endpoint_id`, `endpoint_scheme`, `country`, `street`, `city`, `postal_code`, `registration_name`, `vat`
- New line field: `tax_category` (default "E"), `tax_percent` (default 0)
- Existing fields remain unchanged (backwards compatible at the JSON level)

## Risks / Trade-offs

- **XSD schema bundle size**: The UBL 2.1 XSD package is ~2 MB of XML schema files. This increases the repo size but is a one-time cost and avoids runtime downloads.
- **Element order sensitivity**: Any future additions to the generator must respect UBL element ordering. An ordering mistake only surfaces at XSD validation time, not at runtime.
- **Breaking XML output**: The namespace change means all existing XML output changes structure. This is expected — the current output was never compliant. All tests will be updated.
- **`xmlschema` performance**: Pure Python XSD validation is slower than lxml. For single-invoice validation this is negligible (<1s). If batch validation becomes needed, reconsider lxml.
