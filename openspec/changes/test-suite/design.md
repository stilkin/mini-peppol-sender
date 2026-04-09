## Context

The project has zero automated tests. Three core modules (`ubl.py`, `validator.py`, `api.py`) and a CLI entry point (`cli.py`) need coverage before making larger changes (EN-16931 compliance). All modules are pure functions with no shared state, making them straightforward to test.

## Goals / Non-Goals

**Goals:**
- Set up pytest with project configuration
- Unit tests for all three core modules
- CLI smoke tests verifying the create/validate round-trip
- Tests must pass in CI and via `pre-commit` (optional integration)

**Non-Goals:**
- Integration tests against the live Peppyrus API (requires real credentials)
- 100% coverage — focus on the public API of each module
- Testing EN-16931 fields (that work hasn't landed yet)

## Decisions

**Test framework: pytest**
- Already the de facto standard for Python. Alternatives (unittest, nose2) offer no advantage here.
- Minimal config: just a `[tool.pytest.ini_options]` section in `pyproject.toml`.

**Test layout: `tests/` directory with one module per source module**
- `tests/test_ubl.py`, `tests/test_validator.py`, `tests/test_api.py`, `tests/test_cli.py`
- Mirrors the source structure without over-engineering (no conftest fixtures needed initially).

**No mocking for `ubl.py` and `validator.py`**
- These are pure functions (dict in, bytes out / bytes in, list out). Test with real inputs and assert on outputs.

**Mock HTTP for `api.py` tests**
- `send_message` and `get_report` make real HTTP calls. Use `unittest.mock.patch` on `requests.post`/`requests.get` rather than adding a test dependency like `responses` or `httpx`. Keeps deps minimal.

**CLI smoke tests via `subprocess.run`**
- Run `python cli.py create` and `python cli.py validate` as subprocesses and check exit codes + stdout. This tests the real CLI entry point without importing internals.
- Alternative: use `argparse` programmatically — rejected because it doesn't test the actual user-facing interface.

**`sample_invoice.json` as test fixture**
- Already exists and is known-good. No need to create separate fixture files for now.

## Risks / Trade-offs

- **XML output brittleness**: `generate_ubl()` returns pretty-printed XML. Tests should parse and check elements, not compare raw strings, to avoid breakage from formatting changes.
- **CLI tests depend on file I/O**: smoke tests write temporary files. Use `tmp_path` pytest fixture to keep the test directory clean.
- **No API integration tests**: we won't catch real API contract changes. Acceptable for now — the `en16931-compliance` change will add XSD validation which covers the structural contract.
