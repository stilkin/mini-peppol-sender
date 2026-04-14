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

### Requirement: Local BR-50 check

The validator MUST emit a local FATAL rule when a credit-transfer `PaymentMeansCode` (`30` or `58`) is used without a non-empty `PayeeFinancialAccount/ID` (IBAN). This mirrors PEPPOL BIS Billing 3.0 rule BR-50 and shifts the server-side check left into `validate_basic`.

#### Scenario: Credit transfer without IBAN triggers BR-50

- **WHEN** `validate_basic()` is called on invoice XML containing `PaymentMeansCode` of `30` or `58` and no `PayeeFinancialAccount/ID` (or an empty one)
- **THEN** a FATAL rule with `id: LOCAL-BR-50` and a location pointing to the `cac:PaymentMeans` element is returned

#### Scenario: Credit transfer with IBAN passes

- **WHEN** `validate_basic()` is called on XML containing `PaymentMeansCode` of `30` and a non-empty `PayeeFinancialAccount/ID`
- **THEN** no `LOCAL-BR-50` rule is returned

#### Scenario: BR-50 does not apply to non-credit-transfer codes

- **WHEN** `validate_basic()` is called on XML whose `PaymentMeansCode` is not `30` or `58` (e.g. `10` cash, `20` cheque, `49` direct debit)
- **THEN** no `LOCAL-BR-50` rule is returned regardless of IBAN presence

#### Scenario: BR-50 does not apply when PaymentMeans is absent

- **WHEN** `validate_basic()` is called on XML that contains no `cac:PaymentMeans` element at all
- **THEN** no `LOCAL-BR-50` rule is returned (BR-50 is only triggered by the explicit presence of a credit-transfer code)

### Requirement: CLI validate subcommand

The `validate` subcommand reads an XML file and runs both structural and XSD checks.

#### Scenario: Validate passing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on a valid invoice
- **THEN** the output is `OK: validation passed (no rules)`

#### Scenario: Validate failing invoice

- **WHEN** `cli.py validate --file invoice.xml` is run on an invalid invoice
- **THEN** each triggered rule from both validators is printed
