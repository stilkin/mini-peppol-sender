# Invoice Validation

## ADDED Requirements

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
