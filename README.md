# Peppol Sender

A small tool for generating [EN-16931](https://peppol.org/what-is-peppol/peppol-document-specifications/) compliant UBL 2.1 invoices and sending them to the [PEPPOL](https://peppol.org/) e-invoicing network through the [Peppyrus](https://peppyrus.be/) Access Point API. Ships as both a **command-line tool** and a **single-page web UI**.

## What it does

- **Create** EN-16931 compliant UBL 2.1 XML from a simple JSON input (or a web form)
- **Validate** the XML against the official UBL 2.1 XSD schemas
- **Send** it to the PEPPOL network via Peppyrus, with automatic retry on transient failures
- **Fetch reports** (validation + transmission rules) for sent messages

Designed for a small business that needs to issue invoices themselves, not for enterprise volume. Supports VAT-exempt businesses (tax categories `E` / `O`).

## Technologies

| Layer | Stack |
|---|---|
| Language | Python 3.10+ |
| Package manager | [`uv`](https://docs.astral.sh/uv/) (venv + pip + lockfile in one tool) |
| HTTP client | `requests` + `urllib3.Retry` adapter |
| Configuration | `python-dotenv` |
| XSD validation | `xmlschema` (pure Python) with a cached schema instance |
| Web UI backend | Flask 3 |
| Web UI frontend | Jinja2 templates + vanilla JS + CSS (no build step, no framework) |
| State (web UI) | browser localStorage — no server-side database |
| Bundled schemas | Official OASIS UBL 2.1 XSD files in `schemas/xsd/` |
| Tests | `pytest` + `pytest-cov` (99% coverage, 80% minimum enforced) |
| Lint / type check | `ruff` + `mypy --strict` + `pre-commit` |

PEPPOL BIS Billing 3.0 process type and document type strings are sourced from the Peppyrus OpenAPI spec in `docs/openapi_peppyrus.json`.

## Installation

Requires Python 3.10 or newer. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repo and sync dependencies:

```bash
uv sync              # installs runtime + dev dependencies into .venv
# or
uv sync --no-dev     # runtime dependencies only (smaller install)
```

`uv sync` creates a `.venv/` in the project root, installs everything pinned
via `uv.lock`, and installs the `peppol_sender` package itself in editable
mode. No `pip install`, no `python -m venv` — one command.

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `PEPPYRUS_API_KEY` | Yes | Your Peppyrus API key (test and production are separate keys) |
| `PEPPOL_SENDER_ID` | Yes | Your PEPPOL participant ID (e.g. `0208:0674415660`) |
| `PEPPYRUS_BASE_URL` | No | API base URL. Defaults to the test endpoint `https://api.test.peppyrus.be/v1`. Set to `https://api.peppyrus.be/v1` for production. |

Your API key is read once at process start and stays server-side. The web UI never exposes it to the browser.

## Running the tool

Prefix these with `uv run` (which transparently uses `.venv`), or activate the venv first with `. .venv/bin/activate` and drop the prefix.

### Command-line

```bash
# 1. Generate UBL XML from a JSON invoice
uv run python cli.py create --input sample_invoice.json --out invoice.xml

# 2. Validate it (structural checks + XSD)
uv run python cli.py validate --file invoice.xml

# 3. Send it to a recipient on the PEPPOL network
uv run python cli.py send --file invoice.xml --recipient 0208:be0674415660

# 4. Fetch the validation/transmission report for a sent message
uv run python cli.py report --id <MESSAGE_ID>
```

The `send` command runs validation first and refuses to transmit if any FATAL rules are triggered. API calls retry automatically on 5xx errors with exponential backoff.

See [`docs/invoice-json-schema.md`](docs/invoice-json-schema.md) for the full JSON input format.

### Web UI

```bash
uv run python webapp/app.py
# open http://127.0.0.1:5000
```

Single-page invoice form with:

- **Seller auto-fill** from Peppyrus `/organization/info`
- **Buyer lookup** by VAT number, enriched with PEPPOL directory data
- **Recent customers** and **line item templates** stored in localStorage (overwrite-on-update)
- **Live totals** as you type; strict unit and VAT category dropdowns
- **Auto-incrementing invoice number**
- **Settings modal** for defaults (currency, payment terms, due-date offset, tax category) and your personal contact info (name, email, phone)
- **Validate before send** — FATAL rules block transmission and are shown inline

All persistent state lives in the browser. The Flask server is stateless beyond the environment variables.

## Project structure

```
cli.py                     CLI entry point (create, validate, send, report)
peppol_sender/
  ubl.py                   EN-16931 compliant UBL 2.1 XML generation
  validator.py             Structural + XSD validation (cached schema)
  api.py                   Peppyrus API client with retry
webapp/
  app.py                   Flask app and routes
  templates/index.html     Single-page invoice form
  static/                  CSS + vanilla JS (localStorage-backed state)
tests/                     pytest suite (unit + Flask test client)
schemas/xsd/               Official UBL 2.1 XSD schemas (OASIS)
docs/
  invoice-json-schema.md   Full JSON input reference
  openapi_peppyrus.json    Peppyrus OpenAPI 3.0 specification
openspec/                  Spec-driven change history (archived)
```

## Development

```bash
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run mypy .                        # type check
uv run pytest                        # run the test suite
uv run pytest -k test_name           # run a single test by name
uv run pytest tests/test_ubl.py      # run a single test file
uv run pre-commit run --all-files    # run all pre-commit hooks
```

Dependencies are declared in `pyproject.toml` under `[project]` (runtime) and `[dependency-groups]` (dev). `uv.lock` pins exact versions for reproducible installs. Update the lock with `uv lock --upgrade` or pick a single package with `uv lock --upgrade-package <name>`.

Pre-commit hooks (Ruff + MyPy) are installed via `uv run pre-commit install`. Coverage is enforced at ≥ 80% via `--cov-fail-under=80` in `pyproject.toml` (currently ~99%).

## Limitations

- **No local Schematron / EN-16931 business rule validation.** The tool runs structural checks and XSD validation locally, but Schematron rules (e.g. `BR-CL-14`, `BR-CL-23`, `BR-CO-26`) are caught server-side by Peppyrus after transmission. You can retrieve the report with `cli.py report --id ...` or see the result inline in the web UI.
- **Only the Invoice document type is supported** — no credit notes, debit notes, or other UBL document types.
- **API retry is limited** to 3 attempts on 5xx errors with exponential backoff; there's no persistent retry queue.
- **Single-user assumption** — the web UI has no authentication. The API key in `.env` belongs to one organisation and localStorage state is per-browser.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
