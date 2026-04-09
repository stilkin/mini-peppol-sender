## Why

The `get_report()` API function exists but is not accessible from the CLI, so users cannot check the validation/transmission status of sent invoices without writing custom code. Additionally, API calls have no retry logic — a single network hiccup or 5xx error causes a hard failure.

## What Changes

- Add a `report` subcommand to `cli.py` that fetches and displays the validation/transmission report for a sent message by ID
- Add retry with exponential backoff for API calls on transient failures (5xx status codes and network errors)

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `peppyrus-api`: Add retry/backoff behavior to `send_message` and `get_report`; add CLI `report` subcommand

## Impact

- `cli.py`: New `report` subcommand
- `peppol_sender/api.py`: Retry logic wrapping HTTP calls
- `requirements.txt`: Possibly `urllib3` retry adapter (already a transitive dep of `requests`)
