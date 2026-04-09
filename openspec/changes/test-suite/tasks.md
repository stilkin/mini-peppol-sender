## 1. Setup

- [x] 1.1 Add `pytest` to dev dependencies in `requirements.txt`
- [x] 1.2 Add `[tool.pytest.ini_options]` to `pyproject.toml` (testpaths, strict markers)
- [x] 1.3 Create `tests/` directory with `__init__.py`

## 2. UBL Generation Tests

- [x] 2.1 Create `tests/test_ubl.py` with test for required elements present (ID, IssueDate, AccountingSupplierParty, AccountingCustomerParty, InvoiceLine)
- [x] 2.2 Add test for default values applied when optional fields are omitted
- [x] 2.3 Add test for line item mapping (InvoicedQuantity, LineExtensionAmount, Item/Name, Price/PriceAmount)
- [x] 2.4 Add test for line_extension_amount defaulting to quantity * unit_price

## 3. Validation Tests

- [x] 3.1 Create `tests/test_validator.py` with test for valid XML returning empty rules list
- [x] 3.2 Add test for each missing required element producing a FATAL rule
- [x] 3.3 Add test for unparseable XML returning LOCAL-XML-PARSE FATAL rule

## 4. API Client Tests

- [x] 4.1 Create `tests/test_api.py` with test for `package_message()` base64 encoding round-trip
- [x] 4.2 Add test for `package_message()` output dict structure (all expected keys present)
- [x] 4.3 Add test for `send_message()` with mocked `requests.post` (success response)
- [x] 4.4 Add test for `send_message()` with mocked non-JSON response (error_text fallback)

## 5. CLI Smoke Tests

- [x] 5.1 Create `tests/test_cli.py` with smoke test: `create` subcommand produces XML file
- [x] 5.2 Add smoke test: `validate` subcommand on generated XML prints OK message
- [x] 5.3 Add smoke test: `validate` on invalid XML prints FATAL rules

## 6. Finalize

- [x] 6.1 Run full suite, ensure all tests pass with `ruff check` and `mypy`
- [x] 6.2 Update CLAUDE.md with test commands (`pytest`, `pytest -k test_name`)
