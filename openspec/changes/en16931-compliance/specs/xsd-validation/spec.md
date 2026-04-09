# XSD Validation

## ADDED Requirements

### Requirement: Validate UBL XML against XSD schema

The system MUST validate invoice XML against the official UBL 2.1 XSD schema files
and return structured validation errors compatible with the existing rule format.

#### Scenario: Valid UBL document

- **WHEN** a structurally valid UBL 2.1 invoice XML is validated against the XSD
- **THEN** an empty list of rules is returned

#### Scenario: XSD validation failure

- **WHEN** the XML violates the UBL 2.1 schema (e.g. wrong element order, invalid types)
- **THEN** a list of FATAL rules is returned with the XSD error details

#### Scenario: CLI integration

- **WHEN** `cli.py validate --file invoice.xml` is run
- **THEN** both basic structural checks and XSD validation are performed, and all rules from both are reported
