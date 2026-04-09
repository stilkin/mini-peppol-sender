# Test Infrastructure

## ADDED Requirements

### Requirement: pytest configuration

The project MUST be configured to run tests via `pytest`.

#### Scenario: Run test suite

- **WHEN** `pytest` is executed from the project root
- **THEN** all tests in `tests/` are discovered and run

### Requirement: UBL generation tests

Unit tests MUST verify that `generate_ubl()` produces correct XML.

#### Scenario: Required elements present

- **WHEN** `generate_ubl()` is called with a complete invoice dict
- **THEN** the output XML contains all mandatory UBL elements (ID, IssueDate, AccountingSupplierParty, AccountingCustomerParty, InvoiceLine)

#### Scenario: Default values applied

- **WHEN** `generate_ubl()` is called with a minimal invoice dict (missing optional fields)
- **THEN** default values are applied (invoice_number=INV-0001, unit=EA)

### Requirement: Validation tests

Unit tests MUST verify that `validate_basic()` correctly detects issues.

#### Scenario: Valid XML returns no rules

- **WHEN** valid UBL XML bytes are passed to `validate_basic()`
- **THEN** an empty list is returned

#### Scenario: Missing elements detected

- **WHEN** XML bytes missing required elements are passed to `validate_basic()`
- **THEN** a FATAL rule is returned for each missing element

#### Scenario: Invalid XML detected

- **WHEN** unparseable bytes are passed to `validate_basic()`
- **THEN** a FATAL rule with id `LOCAL-XML-PARSE` is returned

### Requirement: API client tests

Unit tests MUST verify message packaging logic.

#### Scenario: Base64 encoding

- **WHEN** `package_message()` is called with XML bytes
- **THEN** the returned dict contains `fileContent` with valid base64-encoded data that decodes back to the original bytes

### Requirement: CLI smoke tests

Integration tests MUST verify CLI subcommands execute without errors.

#### Scenario: Create and validate round-trip

- **WHEN** `cli.py create` is run on `sample_invoice.json` followed by `cli.py validate` on the output
- **THEN** both commands exit successfully with expected output
