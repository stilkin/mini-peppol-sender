## 1. Setup

- [ ] 1.1 Add `xmlschema` to `requirements.txt` (runtime dependency)
- [ ] 1.2 Download UBL 2.1 XSD package from OASIS and extract `xsd/` subtree into `schemas/`
- [ ] 1.3 Verify the schema loads: `xmlschema.XMLSchema("schemas/xsd/maindoc/UBL-Invoice-2.1.xsd")`

## 2. UBL Generator — Namespaces and Document Header

- [ ] 2.1 Register `cac` and `cbc` namespaces in `ubl.py`, update `_ns()` to support namespace prefixes
- [ ] 2.2 Add document-level elements in correct UBL order: `CustomizationID`, `ProfileID`, `ID`, `IssueDate`, `DueDate`, `InvoiceTypeCode`, `DocumentCurrencyCode`
- [ ] 2.3 Verify generated XML passes XSD validation for the header section

## 3. UBL Generator — Party Details

- [ ] 3.1 Expand `_add_party()` to accept full party dict and generate `EndpointID` (with `@schemeID`), `PostalAddress` (street, city, postal code, country code), `PartyLegalEntity/RegistrationName`
- [ ] 3.2 Add optional `PartyTaxScheme` (VAT number + tax scheme) for parties that have one
- [ ] 3.3 Verify seller and buyer party subtrees pass XSD validation

## 4. UBL Generator — Tax and Totals

- [ ] 4.1 Implement tax grouping: aggregate line items by `(tax_category, tax_percent)`, compute taxable amounts and tax amounts per group
- [ ] 4.2 Generate `TaxTotal` with `TaxAmount` and `TaxSubtotal` entries per group (including `TaxCategory/ID`, `Percent`, `TaxScheme/ID`)
- [ ] 4.3 Support VAT-exempt categories (E/O): zero tax amount, include `TaxExemptionReason`
- [ ] 4.4 Generate `LegalMonetaryTotal` with `LineExtensionAmount`, `TaxExclusiveAmount`, `TaxInclusiveAmount`, `PayableAmount`
- [ ] 4.5 Add optional `PaymentTerms/Note` element

## 5. UBL Generator — Line Item Tax Classification

- [ ] 5.1 Add `ClassifiedTaxCategory` to each `InvoiceLine/Item` with `ID`, `Percent`, and `TaxScheme/ID`

## 6. XSD Validation

- [ ] 6.1 Create `validate_xsd()` function in `validator.py` that validates XML bytes against the UBL 2.1 XSD and returns rule dicts
- [ ] 6.2 Update `cli.py validate` to run both `validate_basic()` and `validate_xsd()`, combining results
- [ ] 6.3 Extend `validate_basic()` required-element list with new mandatory EN-16931 elements

## 7. Sample Data and JSON Schema

- [ ] 7.1 Update `sample_invoice.json` with new fields: `due_date`, `invoice_type_code`, `payment_terms`, seller/buyer address + endpoint + registration_name, line item `tax_category`/`tax_percent`
- [ ] 7.2 Verify end-to-end: `cli.py create` + `cli.py validate` passes with no errors

## 8. Tests

- [ ] 8.1 Update existing `test_ubl.py` tests for new namespace structure and element order
- [ ] 8.2 Add tests for new document-level fields (CustomizationID, ProfileID, InvoiceTypeCode, etc.)
- [ ] 8.3 Add tests for expanded party details (endpoint, address, registration name)
- [ ] 8.4 Add tests for tax calculation: standard VAT, VAT-exempt (category E), mixed rates
- [ ] 8.5 Add tests for LegalMonetaryTotal computation
- [ ] 8.6 Add tests for XSD validation: valid invoice passes, invalid invoice returns FATAL rules
- [ ] 8.7 Update `test_validator.py` for extended required-element checks
- [ ] 8.8 Run full suite, ensure all pass with `ruff`, `mypy`, coverage >= 80%

## 9. Finalize

- [ ] 9.1 Update CLAUDE.md and README to reflect new invoice JSON schema and XSD validation
- [ ] 9.2 Update `ubl-generation` and `invoice-validation` openspec base specs
