# Invoice Validation

Performs structural validation (required EN-16931 element presence) and XSD
validation against the official UBL 2.1 schema.

## ADDED Requirements

### Requirement: Basic structural validation

The validator MUST check for all mandatory EN-16931 elements and return a list of
validation rule dicts. Each rule has keys: `id`, `type` (FATAL or WARNING), `location`, `message`.

#### Scenario: Valid invoice passes

- **WHEN** XML bytes containing all required EN-16931 elements are validated
- **THEN** `validate_basic()` returns an empty list

#### Scenario: Missing required element

- **WHEN** XML bytes are missing one or more required elements
- **THEN** a rule dict with `type: FATAL` and `id: LOCAL-MISSING-<tag>` is returned for each missing element

#### Scenario: Unparseable XML

- **WHEN** XML bytes cannot be parsed
- **THEN** a single rule dict with `id: LOCAL-XML-PARSE` and `type: FATAL` is returned

### Requirement: XSD validation

The system MUST validate invoice XML against the official UBL 2.1 XSD schema files
and return structured validation errors compatible with the existing rule format.

#### Scenario: Valid UBL document

- **WHEN** a structurally valid UBL 2.1 invoice XML is validated against the XSD
- **THEN** an empty list of rules is returned

#### Scenario: XSD validation failure

- **WHEN** the XML violates the UBL 2.1 schema
- **THEN** a list of FATAL rules with `id: XSD-VALIDATION` is returned

### Requirement: CLI validate subcommand

The `validate` subcommand reads an XML file and runs both structural and XSD checks.

#### Scenario: Validate passing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on a valid invoice
- **THEN** the output is `OK: validation passed (no rules)`

#### Scenario: Validate failing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on an invalid invoice
- **THEN** each triggered rule from both validators is printed
