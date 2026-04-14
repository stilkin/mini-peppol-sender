# UBL Generation

## MODIFIED Requirements

### Requirement: Generate UBL invoice from JSON

The generator MUST produce a fully EN-16931 compliant UBL 2.1 Invoice XML from a JSON invoice data structure, including all mandatory fields required by PEPPOL BIS Billing 3.0. When the invoice dict contains a `payment_means` block, a structured `cac:PaymentMeans` element MUST be emitted at the correct UBL sequence position (between `AccountingCustomerParty` and `PaymentTerms`).

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
