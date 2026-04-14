# UBL Generation

Generates EN-16931 compliant UBL 2.1 Invoice XML from a JSON invoice data structure.
Uses proper `cbc:`/`cac:` namespaces and strict element ordering per XSD `xs:sequence`.

## ADDED Requirements

### Requirement: Generate UBL invoice from JSON

The generator MUST produce a fully EN-16931 compliant UBL 2.1 Invoice XML from a
JSON invoice data structure, including all mandatory fields required by PEPPOL BIS Billing 3.0.

#### Scenario: EN-16931 document-level fields

- **WHEN** a valid invoice dict is provided
- **THEN** the generated XML includes `CustomizationID`, `ProfileID`, `ID`, `IssueDate`, `InvoiceTypeCode`, `DocumentCurrencyCode` elements in correct order

#### Scenario: Due date and payment terms

- **WHEN** the invoice dict contains `due_date` and optionally `payment_terms`
- **THEN** `DueDate` and `PaymentTerms/Note` elements are included in the XML

#### Scenario: Seller party with full details

- **WHEN** the invoice dict contains `seller` with `name`, `endpoint_id`, `endpoint_scheme`, `country`, and optionally `street`, `city`, `postal_code`, `vat`
- **THEN** the `AccountingSupplierParty` includes `EndpointID` (with `@schemeID`), `PostalAddress` (with `Country/IdentificationCode`), `PartyLegalEntity/RegistrationName`, and optional `PartyTaxScheme`

#### Scenario: Buyer party with full details

- **WHEN** the invoice dict contains `buyer` with same fields as seller
- **THEN** the `AccountingCustomerParty` includes the same subtree structure

#### Scenario: Legal registration identifier (BT-30/BT-47)

- **WHEN** a party dict contains `legal_id` and optionally `legal_id_scheme`
- **THEN** the `PartyLegalEntity` element includes `CompanyID` with the legal identifier as text and (if present) `legal_id_scheme` as the `@schemeID` attribute

#### Scenario: Party contact information (BT-41..43 / BT-56..58)

- **WHEN** a party dict contains any of `contact_name`, `contact_email`, or `contact_phone`
- **THEN** the party subtree includes a `cac:Contact` element after `PartyLegalEntity`, containing only the fields that are set — `cbc:Name`, `cbc:Telephone`, `cbc:ElectronicMail` — in UBL sequence order

#### Scenario: Legal monetary totals

- **WHEN** the invoice has one or more line items
- **THEN** `LegalMonetaryTotal` is generated with `LineExtensionAmount`, `TaxExclusiveAmount`, `TaxInclusiveAmount`, and `PayableAmount`

#### Scenario: Tax total for VAT-exempt business

- **WHEN** line items use tax category `E` or `O` with percent `0`
- **THEN** `TaxTotal` is generated with `TaxAmount` of `0.00`, a `TaxSubtotal` with the category code, and `TaxExemptionReason`

#### Scenario: Tax total with standard VAT

- **WHEN** line items have a `tax_percent` greater than zero
- **THEN** `TaxTotal` is generated with calculated tax amounts grouped by tax category and rate

#### Scenario: Line item tax classification

- **WHEN** a line item is provided
- **THEN** the `InvoiceLine/Item` includes `ClassifiedTaxCategory` with `ID`, `Percent`, and `TaxScheme/ID` set to `VAT`

#### Scenario: Line service date — single day (BT-134/BT-135)

- **WHEN** a line item contains `service_date`
- **THEN** the `InvoiceLine` includes `cac:InvoicePeriod` after `LineExtensionAmount` with `StartDate` and `EndDate` both set to that value (satisfying `BR-CO-25` which requires both to be present when either is)

#### Scenario: Line service date — range

- **WHEN** a line item contains `service_start_date` and `service_end_date`
- **THEN** the `InvoiceLine` includes `cac:InvoicePeriod` with the provided distinct start and end dates

#### Scenario: Line extension amount defaults

- **WHEN** a line item omits `line_extension_amount`
- **THEN** `LineExtensionAmount` is calculated as `quantity * unit_price`

#### Scenario: Default values

- **WHEN** optional fields are omitted from the invoice dict
- **THEN** defaults are applied: `invoice_number` = `INV-0001`, `invoice_type_code` = `380`, `currency` = `EUR`, `unit` = `EA`, `endpoint_scheme` = `0208`

### Requirement: CLI create subcommand

The `create` subcommand reads a JSON file and writes UBL XML to disk.

#### Scenario: Create invoice from JSON file

- **WHEN** `cli.py create --input invoice.json --out invoice.xml` is run
- **THEN** the JSON file is read, passed to `generate_ubl()`, and the resulting XML is written to the output path
