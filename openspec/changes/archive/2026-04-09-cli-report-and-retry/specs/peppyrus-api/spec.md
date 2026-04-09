# Peppyrus API

## MODIFIED Requirements

### Requirement: Send message to Peppyrus

The client MUST retry transient failures with exponential backoff.

#### Scenario: Retry on server error

- **WHEN** `send_message()` receives a 5xx response or a network error
- **THEN** the request is retried up to 3 times with exponential backoff (1s, 3s, 10s delays)

#### Scenario: No retry on client error

- **WHEN** `send_message()` receives a 4xx response
- **THEN** no retry is attempted and the response is returned immediately

### Requirement: Retrieve message report

The client MUST retry transient failures and the report MUST be accessible via CLI.

#### Scenario: Retry on server error

- **WHEN** `get_report()` receives a 5xx response or a network error
- **THEN** the request is retried up to 3 times with exponential backoff

## ADDED Requirements

### Requirement: CLI report subcommand

The CLI MUST provide a `report` subcommand to fetch and display message reports.

#### Scenario: Fetch report by message ID

- **WHEN** `cli.py report --id <message-id>` is run with valid credentials
- **THEN** the validation and transmission rules from the report are printed

#### Scenario: Missing credentials

- **WHEN** `PEPPYRUS_API_KEY` is not set
- **THEN** an error message is printed and no API call is made
