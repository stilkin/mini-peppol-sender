# UBL Generation

Generates minimal UBL 2.1 Invoice XML from a JSON invoice data structure.

## ADDED Requirements

### Requirement: Generate UBL invoice from JSON

Accepts a dict with invoice header fields, seller, buyer, and line items.
Returns UTF-8 encoded, pretty-printed XML bytes with proper UBL 2.1 namespacing.

#### Scenario: Minimal valid invoice

- **WHEN** a dict with `invoice_number`, `issue_date`, `currency`, `seller.name`, `buyer.name`, and at least one line item is provided
- **THEN** `generate_ubl()` returns UTF-8 XML bytes containing an `Invoice` root element with `ID`, `IssueDate`, `AccountingSupplierParty`, `AccountingCustomerParty`, and `InvoiceLine` children

#### Scenario: Line item fields

- **WHEN** a line item contains `id`, `description`, `quantity`, `unit`, and `unit_price`
- **THEN** the generated `InvoiceLine` element includes `ID`, `InvoicedQuantity` (with `unitCode` attribute), `LineExtensionAmount` (with `currencyID` attribute), `Item/Name`, and `Price/PriceAmount`

#### Scenario: Line extension amount defaults

- **WHEN** a line item omits `line_extension_amount`
- **THEN** `LineExtensionAmount` is calculated as `quantity * unit_price`

#### Scenario: Default values

- **WHEN** optional fields are omitted from the invoice dict
- **THEN** defaults are applied: `invoice_number` = `INV-0001`, `seller.name` = `Seller`, `buyer.name` = `Buyer`, `unit` = `EA`

### Requirement: CLI create subcommand

The `create` subcommand reads a JSON file and writes UBL XML to disk.

#### Scenario: Create invoice from JSON file

- **WHEN** `cli.py create --input invoice.json --out invoice.xml` is run
- **THEN** the JSON file is read, passed to `generate_ubl()`, and the resulting XML is written to the output path
