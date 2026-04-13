## Context

`api.py` has a `get_report()` function that fetches validation/transmission reports for sent messages, but it's not accessible from the CLI. Users must write custom code to check message status. Additionally, all API calls are single-attempt — any transient network or server failure causes a hard error.

The `_parse_response()` helper already centralises response handling, which makes adding retry logic straightforward.

## Goals / Non-Goals

**Goals:**
- Add `report` CLI subcommand to fetch and display message reports
- Add retry with exponential backoff for transient failures (5xx, network errors)
- Tests for both features

**Non-Goals:**
- Retry on client errors (4xx) — these indicate a problem with the request itself
- Polling/waiting for report availability — just fetch once (with retries)
- Persistent retry queue or async retry

## Decisions

**Retry via `urllib3.util.retry.Retry` + `requests.adapters.HTTPAdapter`**
- `urllib3` is already installed as a transitive dependency of `requests` — no new packages needed.
- Configure a `requests.Session` with a mounted retry adapter rather than writing a manual retry loop.
- Retry config: 3 retries, backoff factor 1 (delays: 1s, 2s, 4s), retry on status codes 500/502/503/504.
- The session is created once per API call function. This keeps the functions stateless (no module-level session to manage).
- Alternative considered: manual retry loop with `time.sleep` — rejected because `urllib3` handles edge cases (connection errors, backoff jitter) that a hand-rolled loop would miss.

**Session creation via a private `_session()` helper**
- Returns a `requests.Session` with the retry adapter mounted. Called by `send_message` and `get_report`.
- `package_message` doesn't make HTTP calls, so it's unaffected.

**Report subcommand output format**
- Print validation rules in the same format as `cmd_validate` (type, id, message, location).
- Print transmission rules as-is (the API returns a string).
- If the report has no rules, print a simple "no rules" message.

## Risks / Trade-offs

- **Retry delays block the CLI**: retries with backoff can add up to ~7s of wall time. Acceptable for a CLI tool — the user is waiting for a network response anyway.
- **urllib3 version compatibility**: `Retry` API has been stable across versions. The `status_forcelist` parameter is supported since urllib3 1.x, well before any version bundled with modern `requests`.
