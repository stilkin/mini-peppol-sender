## Why

The project has no automated tests. Any change to the generator, validator, or API client risks silent regressions. Tests are needed before making the larger EN-16931 compliance changes.

## What Changes

- Set up pytest as the test framework
- Add unit tests for `generate_ubl()`: verify required elements are present, check defaults, validate line item mapping
- Add unit tests for `validate_basic()`: valid input, missing elements, parse errors
- Add unit tests for `package_message()`: verify base64 encoding and message structure
- Add CLI smoke tests: verify subcommands run without errors on sample data

## Capabilities

### New Capabilities

- `test-infrastructure`: pytest configuration and test suite covering core modules

### Modified Capabilities

_None_

## Impact

- New `tests/` directory with test modules
- `requirements.txt`: Add `pytest` as dev dependency
- `pyproject.toml`: Add pytest configuration
