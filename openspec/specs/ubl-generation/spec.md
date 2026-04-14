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

#### Scenario: Payment means — credit transfer with IBAN

- **WHEN** the invoice dict contains `payment_means` with an `iban` and optional `bic`, `account_name`, `payment_id`, and `code`
- **THEN** the generated XML includes `cac:PaymentMeans` positioned after `AccountingCustomerParty` and before `PaymentTerms`, containing `cbc:PaymentMeansCode` (value from `code`), optional `cbc:PaymentID`, and `cac:PayeeFinancialAccount` with `cbc:ID` (the IBAN), optional `cbc:Name` (the account holder), and optional `cac:FinancialInstitutionBranch/cbc:ID` (the BIC)

#### Scenario: Payment means defaults

- **WHEN** `payment_means` contains `iban` but omits `code`, `account_name`, and `payment_id`
- **THEN** `PaymentMeansCode` defaults to `"30"` (credit transfer), `Name` defaults to the seller name, and `PaymentID` defaults to the invoice number

#### Scenario: BIC is optional

- **WHEN** `payment_means` omits `bic`
- **THEN** no `cac:FinancialInstitutionBranch` element is emitted under `PayeeFinancialAccount`

#### Scenario: No payment means block

- **WHEN** the invoice dict does not contain a `payment_means` key
- **THEN** no `cac:PaymentMeans` element is emitted and the rest of the invoice XML is unchanged

#### Scenario: Non-credit-transfer payment codes

- **WHEN** `payment_means.code` is a non-credit-transfer value (e.g. `"10"` for cash, `"20"` for cheque)
- **THEN** `cac:PaymentMeans` is still emitted with the given code and with `PayeeFinancialAccount` populated only if an `iban` is supplied

#### Scenario: Embed visual representation (PDF)

- **WHEN** `generate_ubl()` is called with `embed_pdf=True` (the CLI and webapp default at their call sites)
- **THEN** the generated XML contains exactly one `cac:AdditionalDocumentReference` positioned after `cbc:BuyerReference` and before `cac:AccountingSupplierParty`, containing `cbc:ID` (the invoice number), `cbc:DocumentDescription` (`"Commercial Invoice"`), and `cac:Attachment/cbc:EmbeddedDocumentBinaryObject` with `mimeCode="application/pdf"`, `filename="<invoice_number>.pdf"`, and base64-encoded PDF bytes as element text

#### Scenario: Single visual representation per invoice

- **WHEN** an invoice is generated with PDF embedding enabled
- **THEN** exactly one `cac:AdditionalDocumentReference` with an embedded PDF is emitted (matching PEPPOL-EN16931-R008)

#### Scenario: PDF embedding opt-out

- **WHEN** `generate_ubl()` is called with `embed_pdf=False` (the library default)
- **THEN** no `cac:AdditionalDocumentReference` element is emitted and the rest of the XML is unchanged

#### Scenario: PDF totals match XML totals

- **WHEN** an invoice is rendered and embedded
- **THEN** the totals displayed in the PDF (subtotal, tax, grand total) match the XML's `LegalMonetaryTotal/PayableAmount` and `TaxTotal/TaxAmount` byte-for-byte, including for mixed-rate invoices (same tax-group Decimal rounding as `_add_tax_total`)

### Requirement: CLI create subcommand

The `create` subcommand reads a JSON file and writes UBL XML to disk.

#### Scenario: Create invoice from JSON file

- **WHEN** `cli.py create --input invoice.json --out invoice.xml` is run
- **THEN** the JSON file is read, passed to `generate_ubl()`, and the resulting XML is written to the output path
