# UBL Generation

## MODIFIED Requirements

### Requirement: Generate UBL invoice from JSON

The generator MUST produce a fully EN-16931 compliant UBL 2.1 Invoice XML from a
JSON invoice data structure, including all mandatory fields required by PEPPOL BIS Billing 3.0.

#### Scenario: EN-16931 document-level fields

- **WHEN** a valid invoice dict is provided
- **THEN** the generated XML includes `CustomizationID`, `ProfileID`, `InvoiceTypeCode`, `DocumentCurrencyCode`, and `DueDate` elements with correct values

#### Scenario: Seller party with full details

- **WHEN** the invoice dict contains `seller` with `name`, `endpoint_id`, `endpoint_scheme`, `country`, and optionally `street`, `city`, `postal_code`
- **THEN** the `AccountingSupplierParty` includes `EndpointID` (with `@schemeID`), `PostalAddress` (with `Country/IdentificationCode`), and `PartyLegalEntity/RegistrationName`

#### Scenario: Buyer party with full details

- **WHEN** the invoice dict contains `buyer` with `name`, `endpoint_id`, `endpoint_scheme`, `country`, and optionally `street`, `city`, `postal_code`
- **THEN** the `AccountingCustomerParty` includes `EndpointID` (with `@schemeID`), `PostalAddress` (with `Country/IdentificationCode`), and `PartyLegalEntity/RegistrationName`

#### Scenario: Legal monetary totals

- **WHEN** the invoice has one or more line items
- **THEN** `LegalMonetaryTotal` is generated with `LineExtensionAmount` (sum of line amounts), `TaxExclusiveAmount`, `TaxInclusiveAmount`, and `PayableAmount`

#### Scenario: Tax total for VAT-exempt business

- **WHEN** line items use tax category `E` (exempt) or `O` (not subject to VAT) with percent `0`
- **THEN** `TaxTotal` is generated with `TaxAmount` of `0.00` and a `TaxSubtotal` containing the category code, zero rate, and `TaxExemptionReason`

#### Scenario: Tax total with standard VAT

- **WHEN** line items have a `tax_percent` greater than zero
- **THEN** `TaxTotal` is generated with calculated tax amounts grouped by tax category and rate

#### Scenario: Line item tax classification

- **WHEN** a line item is provided
- **THEN** the `InvoiceLine/Item` includes `ClassifiedTaxCategory` with `ID`, `Percent`, and `TaxScheme/ID` set to `VAT`

#### Scenario: Payment terms and due date

- **WHEN** the invoice dict contains `due_date` and optionally `payment_terms`
- **THEN** `DueDate` and `PaymentTerms/Note` elements are included in the XML
