# Invoice Validation

Performs lightweight structural validation on UBL invoice XML before sending.

## ADDED Requirements

### Requirement: Basic structural validation

Checks for presence of required UBL elements and returns a list of validation
rule dicts. Each rule has keys: `id`, `type` (FATAL or WARNING), `location`, `message`.

#### Scenario: Valid invoice passes

- **WHEN** XML bytes containing all required elements (ID, IssueDate, AccountingSupplierParty, AccountingCustomerParty, InvoiceLine) are validated
- **THEN** `validate_basic()` returns an empty list

#### Scenario: Missing required element

- **WHEN** XML bytes are missing one or more required elements
- **THEN** a rule dict with `type: FATAL` and `id: LOCAL-MISSING-<tag>` is returned for each missing element

#### Scenario: Unparseable XML

- **WHEN** XML bytes cannot be parsed
- **THEN** a single rule dict with `id: LOCAL-XML-PARSE` and `type: FATAL` is returned

### Requirement: CLI validate subcommand

The `validate` subcommand reads an XML file and prints validation results.

#### Scenario: Validate passing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on a valid invoice
- **THEN** the output is `OK: basic validation passed (no rules)`

#### Scenario: Validate failing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on an invoice with missing elements
- **THEN** each triggered rule is printed with its type, id, message, and location
