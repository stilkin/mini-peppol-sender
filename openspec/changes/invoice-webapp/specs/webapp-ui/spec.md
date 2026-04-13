# Webapp UI

## ADDED Requirements

### Requirement: Invoice form layout

The webapp MUST provide a single-page invoice form with sections for seller, buyer, line items, and invoice settings.

#### Scenario: Page load with seller auto-population

- **WHEN** the user opens the invoice form
- **THEN** seller fields (name, address, VAT, endpoint ID) are pre-filled from the Peppyrus organization info API and displayed as read-only

#### Scenario: Invoice header defaults

- **WHEN** the form loads
- **THEN** invoice number is auto-incremented from the last used number stored in localStorage, issue date defaults to today, and saved defaults (currency, payment terms, due date offset, tax category/percent) are applied

### Requirement: Buyer lookup and selection

The webapp MUST allow looking up PEPPOL participants and selecting from recent customers.

#### Scenario: Lookup buyer by VAT number

- **WHEN** the user enters a VAT number and country code, then clicks "Lookup"
- **THEN** the app queries the Peppyrus `/peppol/bestMatch` endpoint and pre-fills the buyer's participant ID and available details

#### Scenario: Select recent customer

- **WHEN** the user opens the customer dropdown
- **THEN** previously used buyers (stored in localStorage) are listed, and selecting one pre-fills all buyer fields

#### Scenario: Save new customer

- **WHEN** an invoice is successfully sent to a new buyer
- **THEN** the buyer details are saved to localStorage for future use

### Requirement: Dynamic line items

The webapp MUST support adding, removing, and templating line items with auto-calculated totals.

#### Scenario: Add and remove line rows

- **WHEN** the user clicks "Add line" or "Remove" on a line
- **THEN** a row is added or removed, and totals are recalculated

#### Scenario: Line item templates

- **WHEN** the user selects a saved line template from a dropdown
- **THEN** the description, unit, unit price, tax category, and tax percent fields are pre-filled

#### Scenario: Save line template

- **WHEN** the user clicks "Save as template" on a line item
- **THEN** the line item details are stored in localStorage for future use

#### Scenario: Auto-calculated totals

- **WHEN** line item quantities, prices, or tax rates change
- **THEN** line extension amounts, tax totals, and the grand total are recalculated and displayed in real time

### Requirement: Validate and send

The webapp MUST validate invoices before sending and display clear results.

#### Scenario: Validate before send

- **WHEN** the user clicks "Send"
- **THEN** the invoice is validated (basic + XSD) first; if FATAL rules are found, they are displayed and the send is blocked

#### Scenario: Successful send

- **WHEN** validation passes and the invoice is sent
- **THEN** the HTTP status and message ID are displayed, the invoice number is incremented in localStorage, and the buyer is saved to recent customers

#### Scenario: Send failure

- **WHEN** the API returns an error
- **THEN** the error details are displayed to the user

### Requirement: Settings management

The webapp MUST allow users to view and edit their default invoice settings.

#### Scenario: Edit defaults

- **WHEN** the user opens a settings panel
- **THEN** they can edit default currency, payment terms, due date offset, and tax category/percent, which are saved to localStorage
