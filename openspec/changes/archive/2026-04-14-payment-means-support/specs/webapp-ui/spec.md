# Webapp UI

## ADDED Requirements

### Requirement: Seller bank account settings

The Settings modal MUST allow the user to configure seller bank account details (IBAN, BIC, account holder name) as a persistent default, alongside the existing currency / payment terms / due date offset / tax category defaults. These values MUST be persisted in browser localStorage and MUST be included in the `payment_means` block of every invoice JSON sent to `/api/validate` and `/api/send`.

#### Scenario: Edit and persist bank account details

- **WHEN** the user opens the Settings modal, fills in IBAN, BIC, and account holder name, and clicks Save
- **THEN** the values are stored in localStorage and the modal closes

#### Scenario: Bank details auto-apply to new invoices

- **WHEN** a new invoice form is opened after saving bank details in settings
- **THEN** the saved values are available without re-entry and are included in `payment_means` on validate/send

#### Scenario: Bank details in validate and send payloads

- **WHEN** the user clicks Validate or Send on an invoice with configured bank details
- **THEN** the POST body contains a `payment_means` block with `iban`, `bic` (if set), and `account_name`, and the backend forwards it to `generate_ubl()`

#### Scenario: Misleading IBAN placeholder removed

- **WHEN** the user opens the invoice form
- **THEN** the `Payment terms` textarea no longer shows an `IBAN: BE00 ...` placeholder; its placeholder text refers only to payment notes (e.g. `Net 21 days`)
