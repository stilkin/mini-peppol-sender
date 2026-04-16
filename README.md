<p align="center">
  <img src="docs/peppify_logo.png" alt="Peppify" width="436" />
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm_NC_1.0-blue" alt="License"></a>
  <a href="https://docs.astral.sh/ruff/"><img src="https://img.shields.io/badge/code_style-ruff-D7FF64?logo=ruff&logoColor=D7FF64" alt="Ruff"></a>
  <a href="https://mypy-lang.org/"><img src="https://img.shields.io/badge/type_checked-mypy-blue" alt="mypy"></a>
  <a href="https://ko-fi.com/stilkin"><img src="https://img.shields.io/badge/Ko--fi-F16061?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
</p>

---

A small tool for generating [EN-16931](https://peppol.org/what-is-peppol/peppol-document-specifications/) compliant UBL 2.1 invoices and sending them to the [PEPPOL](https://peppol.org/) e-invoicing network through the [Peppyrus](https://peppyrus.be/) Access Point API. Ships as both a **command-line tool** and a **single-page web UI**.

## What it does

- **Create** EN-16931 compliant UBL 2.1 XML from a simple JSON input (or a web form)
- **Render** a human-readable PDF "visual representation" of the invoice and embed it inside the UBL XML (PEPPOL BIS Billing 3.0 rule R008) so receivers' accountancy software has something to show end users. The PDF is translated per-invoice into one of four languages (**EN / NL / FR / DE**) with human-readable unit names and BeNeLux number formatting (`1.234,56`), and includes an **EPC QR Code** (SEPA / Girocode) on EUR credit-transfer invoices so the recipient can scan it with their banking app to pre-fill IBAN, beneficiary, amount, and reference
- **Validate** the XML against the official UBL 2.1 XSD schemas
- **Send** it to the PEPPOL network via Peppyrus, with automatic retry on transient failures
- **Fetch reports** (validation + transmission rules) for sent messages

Designed for a small business that needs to issue invoices themselves, not for enterprise volume. Supports VAT-exempt businesses (tax categories `E` / `O`) and emits structured payment details (`cac:PaymentMeans` with IBAN / BIC) so receivers' bookkeeping software can auto-reconcile — bank details live in the structured `payment_means` block, **not** in the free-form `payment_terms` note.

## Technologies

| Layer | Stack |
|---|---|
| Language | Python 3.10+ |
| Package manager | [`uv`](https://docs.astral.sh/uv/) (venv + pip + lockfile in one tool) |
| HTTP client | `requests` + `urllib3.Retry` adapter |
| Configuration | `python-dotenv` |
| XSD validation | `xmlschema` (pure Python) with a cached schema instance |
| PDF rendering | [WeasyPrint](https://weasyprint.org/) + Jinja2 (HTML template → PDF) |
| Web UI backend | Flask 3 |
| Web UI frontend | Jinja2 templates + vanilla JS + CSS (no build step, no framework) |
| State (web UI) | browser localStorage — no server-side database |
| Bundled schemas | Official OASIS UBL 2.1 XSD files in `schemas/xsd/` |

PEPPOL BIS Billing 3.0 process type and document type strings are sourced from the Peppyrus OpenAPI spec in `docs/openapi_peppyrus.json`.

## Installation

Requires Python 3.10 or newer. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### System prerequisites (WeasyPrint)

PDF rendering uses [WeasyPrint](https://weasyprint.org/), which needs Pango, Cairo, and libgdk-pixbuf at the OS level. Install them once with your package manager:

```bash
# Debian / Ubuntu
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf2.0-0

# Fedora
sudo dnf install pango cairo gdk-pixbuf2

# macOS (Homebrew)
brew install pango cairo gdk-pixbuf
```

Most modern desktop Linux distros already have these. If the libraries are missing, the library still imports and XML generation still works — only `render_pdf()` (and the CLI's default PDF embedding) will raise a clear `RuntimeError` pointing back to this section.

### Python dependencies

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
# 1. Generate UBL XML from a JSON invoice (embeds a rendered PDF by default)
uv run python cli.py create --input sample_invoice.json --out invoice.xml

# 1b. XML-only output (skip the embedded PDF)
uv run python cli.py create --input sample_invoice.json --out invoice.xml --no-pdf

# 1c. Override the PDF language (en / nl / fr / de — falls back to invoice JSON or 'en')
uv run python cli.py create --input sample_invoice.json --out invoice.xml --language nl

# 1d. Generate a UBL Credit Note instead of an Invoice
uv run python cli.py create --type credit-note --input credit_note.json --out cn.xml --no-pdf

# 2. Validate it — works on both invoices and credit notes (document type auto-detected)
uv run python cli.py validate --file invoice.xml

# 3. Send it to a recipient on the PEPPOL network — document type auto-detected from the XML root
uv run python cli.py send --file invoice.xml --recipient 0208:be0674415660

# 4. Fetch the validation/transmission report for a sent message
uv run python cli.py report --id <MESSAGE_ID>
```

The `send` command runs validation first and refuses to transmit if any FATAL rules are triggered. Idempotent API calls (report, lookup) retry automatically on 5xx errors with exponential backoff; the actual `POST /message` is **not** retried to avoid duplicate transmissions.

See [`docs/invoice-json-schema.md`](docs/invoice-json-schema.md) for the full JSON input format.

### Web UI

#### Development

```bash
uv run python webapp/app.py
# open http://127.0.0.1:5000
```

Flask's built-in dev server. Fine for local iteration; prints a Werkzeug warning because it is not a production server.

#### Production (Python)

```bash
uv sync --group prod
uv run gunicorn webapp.app:app -b 127.0.0.1:5000 --workers 2
# open http://127.0.0.1:5000
```

Same app, served by gunicorn — no dev-server warning. Requires a working Python + `uv` environment with the system-level Pango/Cairo libraries WeasyPrint needs.

#### Production (Docker)

```bash
cp .env.example .env   # fill in PEPPYRUS_* values
docker compose up --build
# open http://127.0.0.1:5000
```

The image bundles Python, the pinned dependencies, and all native libraries required for PDF rendering — no host install beyond Docker itself. The compose file binds the app to `127.0.0.1` on the host; see **Security** below before exposing it further.

Single-page invoice form with:

- **Seller auto-fill** from Peppyrus `/organization/info`
- **Buyer lookup** by VAT number, enriched with PEPPOL directory data
- **Recent customers** and **line item templates** stored in localStorage (overwrite-on-update), with a small `×` next to the Recent dropdown to delete a single saved customer
- **Line items** with optional **per-line service date** (UBL `cac:InvoicePeriod`)
- **Live totals** as you type; strict unit and VAT category dropdowns
- **Auto-incrementing invoice number**
- **New invoice** button (`＋`) in the header — wipes the current draft and starts fresh while keeping all saved state; silent when the previous draft was already sent, confirms otherwise
- **PDF language selector** next to the Currency field — pick EN / NL / FR / DE per invoice. The chosen language is saved on the customer record so the next invoice to the same customer auto-fills it, and a `Default PDF language` in Settings is the fallback for new customers
- **Settings modal** for defaults (currency, default PDF language, due-date offset, payment terms, tax category, **embed PDF on/off**), your **bank account** (IBAN, BIC, account holder — emitted as structured `cac:PaymentMeans` on every invoice to satisfy PEPPOL rule BR-50), and your personal contact info (name, email, phone). A **Danger zone** at the bottom offers a one-click factory reset that wipes every Peppify key from localStorage
- **Preview PDF** button — see the human-readable representation that will be embedded in the invoice before you send it
- **Guarded Send** — the `Send invoice` button stays disabled until you click `Validate` and no FATAL rules remain; rules are shown inline and block transmission either way
- **Recipient derived from the buyer** — the outgoing PEPPOL `recipient` is built on the fly from the buyer's `Scheme` + `Endpoint ID` fields, so you only enter the identifier once

All persistent state lives in the browser. The Flask server is stateless beyond the environment variables.

## Security

The webapp has **no built-in authentication**. Anyone who can reach the HTTP port can create, validate, and send invoices signed with your Peppyrus API key.

All documented run modes bind the app to `127.0.0.1`, so out of the box it is only reachable from the machine it runs on. If you want to expose it beyond localhost (LAN or internet), you **must** put an authenticating reverse proxy (Caddy, Traefik, nginx + basic-auth, your SSO of choice) in front of it. Changing the bind address to `0.0.0.0` without such a proxy is unsafe.

## Limitations

- **No local Schematron / EN-16931 business rule validation.** The tool runs structural checks and XSD validation locally, but Schematron rules (e.g. `BR-CL-14`, `BR-CL-23`, `BR-CO-26`) are caught server-side by Peppyrus after transmission. You can retrieve the report with `cli.py report --id ...` or see the result inline in the web UI.
- **Credit notes are CLI-only.** `cli.py create --type credit-note` and `cli.py send` produce and transmit compliant UBL 2.1 Credit Notes (EN-16931 / PEPPOL BIS Billing 3.0). The web UI does not yet offer a credit-note form — use the CLI until the follow-up change lands.
- **Debit notes and other UBL document types** are not supported.
- **API retry is limited** to 3 attempts on 5xx errors with exponential backoff; there's no persistent retry queue.
- **Single-user assumption** — the web UI has no authentication. The API key in `.env` belongs to one organisation and localStorage state is per-browser.

## Contributing

See [`docs/development.md`](docs/development.md) for project structure, linting, testing, and dependency management.

## Support

If you enjoy Peppify and want to support its development, consider buying me a drink:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/stilkin)

Your support helps me continue developing and improving Peppify!

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
