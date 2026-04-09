## 1. Retry Logic

- [x] 1.1 Add `_session()` helper in `api.py` that returns a `requests.Session` with `HTTPAdapter` + `Retry` (3 retries, backoff factor 1, status_forcelist=[500, 502, 503, 504])
- [x] 1.2 Update `send_message()` to use `_session()` instead of bare `requests.post`
- [x] 1.3 Update `get_report()` to use `_session()` instead of bare `requests.get`

## 2. CLI Report Subcommand

- [x] 2.1 Add `cmd_report()` function in `cli.py` that reads env vars, calls `get_report()`, and prints validation/transmission rules
- [x] 2.2 Register `report` subparser with `--id` (required) argument in `main()`

## 3. Tests

- [x] 3.1 Add test for retry on 5xx: mock a sequence of 503 then 200 responses, assert success
- [x] 3.2 Add test for no retry on 4xx: mock a 422 response, assert returned immediately
- [x] 3.3 Add test for `cmd_report` CLI smoke test (mock API or check arg parsing)

## 4. Finalize

- [x] 4.1 Run full suite (`pytest`, `ruff check`, `mypy`), ensure all pass
- [x] 4.2 Update CLAUDE.md and README with `report` subcommand usage
