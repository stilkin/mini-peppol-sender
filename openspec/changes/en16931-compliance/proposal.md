## Why

The current UBL generator produces a minimal invoice that is missing ~15 mandatory EN-16931 fields, causing FATAL business rule failures (BR-01 through BR-63) when submitted to a PEPPOL access point. Without these fields, no invoice can be successfully transmitted. Additionally, there is no XSD validation to catch structural errors before sending.

## What Changes

- Extend `ubl.py` to generate all mandatory EN-16931 / PEPPOL BIS Billing 3.0 fields:
  - Document-level: `CustomizationID`, `ProfileID`, `InvoiceTypeCode`, `DocumentCurrencyCode`, `DueDate`
  - Seller/Buyer parties: `EndpointID`, `PostalAddress` (with country code), `PartyLegalEntity/RegistrationName`, optional `PartyTaxScheme`
  - Totals: `LegalMonetaryTotal` (line sum, tax-exclusive, tax-inclusive, payable amount)
  - Tax: `TaxTotal` with `TaxSubtotal` (supports category E/O for VAT-exempt businesses)
  - Line items: `ClassifiedTaxCategory` with tax scheme
  - Optional: `PaymentTerms`, seller/buyer address fields (street, city, postal code)
- Update `sample_invoice.json` to include new fields (due_date, invoice_type_code, endpoint IDs)
- Add XSD validation using `lxml` or `xmlschema` against official UBL 2.1 XSD schemas
- Bundle or reference the UBL 2.1 XSD schema files

## Capabilities

### New Capabilities

- `xsd-validation`: XSD schema validation of UBL 2.1 invoices using official schema files

### Modified Capabilities

- `ubl-generation`: Add all mandatory EN-16931 fields to the generator, update JSON input schema
- `invoice-validation`: Add XSD validation as a step alongside the existing structural checks

## Impact

- `peppol_sender/ubl.py`: Major changes — new elements, updated party builder, totals/tax calculation
- `peppol_sender/validator.py`: Add XSD validation function
- `sample_invoice.json`: Extended with new required fields
- `requirements.txt`: New dependency (`lxml` or `xmlschema`)
- `cli.py`: No changes expected (existing validate/create commands work as before)
