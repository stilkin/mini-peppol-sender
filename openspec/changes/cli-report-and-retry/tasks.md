## 1. Retry Logic

- [ ] 1.1 Add `_session()` helper in `api.py` that returns a `requests.Session` with `HTTPAdapter` + `Retry` (3 retries, backoff factor 1, status_forcelist=[500, 502, 503, 504])
- [ ] 1.2 Update `send_message()` to use `_session()` instead of bare `requests.post`
- [ ] 1.3 Update `get_report()` to use `_session()` instead of bare `requests.get`

## 2. CLI Report Subcommand

- [ ] 2.1 Add `cmd_report()` function in `cli.py` that reads env vars, calls `get_report()`, and prints validation/transmission rules
- [ ] 2.2 Register `report` subparser with `--id` (required) argument in `main()`

## 3. Tests

- [ ] 3.1 Add test for retry on 5xx: mock a sequence of 503 then 200 responses, assert success
- [ ] 3.2 Add test for no retry on 4xx: mock a 422 response, assert returned immediately
- [ ] 3.3 Add test for `cmd_report` CLI smoke test (mock API or check arg parsing)

## 4. Finalize

- [ ] 4.1 Run full suite (`pytest`, `ruff check`, `mypy`), ensure all pass
- [ ] 4.2 Update CLAUDE.md and README with `report` subcommand usage
