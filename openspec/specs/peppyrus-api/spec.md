# Peppyrus API

Client for the Peppyrus Access Point API. Handles packaging invoices into the
required MessageBody format and transmitting them over HTTPS. API calls retry
automatically on transient server errors (5xx) with exponential backoff.

## ADDED Requirements

### Requirement: Package message for transmission

Base64-encodes invoice XML and wraps it in a MessageBody dict matching the
Peppyrus OpenAPI schema.

#### Scenario: Package valid invoice

- **WHEN** `package_message()` is called with XML bytes, sender, recipient, process type, and document type
- **THEN** a dict is returned with keys `sender`, `recipient`, `processType`, `documentType`, and `fileContent` (base64-encoded XML)

### Requirement: Send message to Peppyrus

POSTs the packaged MessageBody to the Peppyrus `/message` endpoint with
`X-Api-Key` authentication. The client MUST retry transient failures with
exponential backoff.

#### Scenario: Successful send

- **WHEN** `send_message()` is called with a valid message body and API key
- **THEN** a dict with `status_code` and `json` (parsed response body) is returned

#### Scenario: Non-JSON response

- **WHEN** the API returns a non-JSON response body
- **THEN** `json` contains `{"error_text": "<raw response text>"}`

#### Scenario: Retry on server error

- **WHEN** `send_message()` receives a 5xx response or a network error
- **THEN** the request is retried up to 3 times with exponential backoff (1s, 3s, 10s delays)

#### Scenario: No retry on client error

- **WHEN** `send_message()` receives a 4xx response
- **THEN** no retry is attempted and the response is returned immediately

### Requirement: Retrieve message report

Fetches validation and transmission rules for a previously sent message via
`GET /message/{id}/report`. The client MUST retry transient failures.

#### Scenario: Fetch report

- **WHEN** `get_report()` is called with a message ID and API key
- **THEN** a dict with `status_code` and `json` (parsed report) is returned

#### Scenario: Retry on server error

- **WHEN** `get_report()` receives a 5xx response or a network error
- **THEN** the request is retried up to 3 times with exponential backoff

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

### Requirement: CLI report subcommand

The CLI MUST provide a `report` subcommand to fetch and display message reports.

#### Scenario: Fetch report by message ID

- **WHEN** `cli.py report --id <message-id>` is run with valid credentials
- **THEN** the validation and transmission rules from the report are printed

#### Scenario: Missing credentials

- **WHEN** `PEPPYRUS_API_KEY` is not set
- **THEN** an error message is printed and no API call is made
