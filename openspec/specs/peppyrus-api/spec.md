# Peppyrus API

Client for the Peppyrus Access Point API. Handles packaging invoices into the
required MessageBody format and transmitting them over HTTPS.

## ADDED Requirements

### Requirement: Package message for transmission

Base64-encodes invoice XML and wraps it in a MessageBody dict matching the
Peppyrus OpenAPI schema.

#### Scenario: Package valid invoice

- **WHEN** `package_message()` is called with XML bytes, sender, recipient, process type, and document type
- **THEN** a dict is returned with keys `sender`, `recipient`, `processType`, `documentType`, and `fileContent` (base64-encoded XML)

### Requirement: Send message to Peppyrus

POSTs the packaged MessageBody to the Peppyrus `/message` endpoint with
`X-Api-Key` authentication.

#### Scenario: Successful send

- **WHEN** `send_message()` is called with a valid message body and API key
- **THEN** a dict with `status_code` and `json` (parsed response body) is returned

#### Scenario: Non-JSON response

- **WHEN** the API returns a non-JSON response body
- **THEN** `json` contains `{"error_text": "<raw response text>"}`

### Requirement: Retrieve message report

Fetches validation and transmission rules for a previously sent message via
`GET /message/{id}/report`.

#### Scenario: Fetch report

- **WHEN** `get_report()` is called with a message ID and API key
- **THEN** a dict with `status_code` and `json` (parsed report) is returned

### Requirement: CLI send subcommand

The `send` subcommand validates, packages, and transmits an invoice.
Requires `PEPPYRUS_API_KEY` and `PEPPOL_SENDER_ID` environment variables.

#### Scenario: Send with valid credentials

- **WHEN** `cli.py send --file invoice.xml --recipient <ID>` is run with valid env vars
- **THEN** the invoice is validated, packaged, sent, and the HTTP status code and response are printed

#### Scenario: Abort on FATAL validation

- **WHEN** the invoice has FATAL validation rules
- **THEN** the send is aborted and the fatal rules are printed

#### Scenario: Missing credentials

- **WHEN** `PEPPYRUS_API_KEY` or `PEPPOL_SENDER_ID` is not set
- **THEN** an error message is printed and no API call is made
