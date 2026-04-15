## 1. i18n Module

- [x] 1.1 Create `peppol_sender/i18n.py` with module-level dicts: `_TRANSLATIONS` (lang → key → string) and `_UNIT_NAMES` (lang → unit code → name). Cover the four languages (EN, NL, FR, DE) for every key and every unit code in the existing `UNIT_CODES` list from `webapp/static/app.js`
- [x] 1.2 Define the canonical label key set. 21 keys: `invoice`, `from`, `bill_to`, `description`, `qty`, `unit`, `unit_price`, `line_total`, `subtotal`, `tax`, `total_due`, `payment`, `please_transfer_to`, `scan_with_banking_app`, `service_date`, `reference`, `vat`, `bic`, `issued`, `due`, `ref`
- [x] 1.3 Implement `t(lang: str, key: str) -> str` with two-level fallback: requested language → English → key name. Case-insensitive on the language code
- [x] 1.4 Implement `unit_label(lang: str, code: str) -> str` with two-level fallback: requested language → English → raw code
- [x] 1.5 Implement `format_amount(value: Decimal) -> str` returning BeNeLux notation (`.` thousands, `,` decimals, always 2 decimal places). No language parameter — one canonical format for every PDF
- [x] 1.6 Implement `all_labels(lang: str) -> dict[str, str]` as a convenience that builds the full labels dict for a given language, so `_build_view_model()` can hand the template a single object rather than calling `t()` per string
- [x] 1.7 Draft the NL / FR / DE translations for all label keys and unit codes. User reviewed the draft table in the plan file before implementation and approved. French uses non-breaking space (`\u00a0`) before colons per typographic convention

## 2. PDF Rendering Integration

- [x] 2.1 Extend `peppol_sender/pdf.py`'s `_build_view_model()` to read `invoice.get("language", "en").lower()` and build `labels = i18n.all_labels(lang)`; attach `labels` and `language` to the view model
- [x] 2.2 Within the display-lines loop, set `line["unit_label"] = i18n.unit_label(lang, raw_unit_code)` so the template can render the translated name; the raw `unit` key is kept alongside for any future structural use
- [x] 2.3 Replace the three formatted total strings (`subtotal`, `tax_total`, `grand_total`) with `i18n.format_amount(Decimal)` outputs (BeNeLux style). Line-level `unit_price` and `line_total` also use `format_amount` inside the display-lines loop
- [x] 2.4 Confirmed the amount string threaded into `build_epc_payload(invoice, grand_total_dec)` still uses the ASCII `EUR1234.56` format — `epc_qr.py` takes a raw `Decimal` and formats internally with `f"EUR{grand_total:.2f}"`, so the pdf.py string-format change does not leak into the EPC payload. Added `test_payload_amount_stays_ascii_regardless_of_language` in `test_epc_qr.py` as a forward guardrail
- [x] 2.5 Updated `peppol_sender/templates/invoice.html` to read every user-facing string from `{{ labels.<key> }}` — `Invoice`, `Issued`, `Due`, `Ref`, `From`, `Bill to`, `VAT`, `Description`, `Qty`, `Unit`, `Unit price`, `Line total`, `Service date:`, `Subtotal`, `Tax`, `Total due`, `Payment`, `Please transfer to:`, `BIC`, `Reference:`, `Scan with your banking app`
- [x] 2.6 Updated the line-items table in the template to render `{{ line.unit_label }}` instead of `{{ line.unit }}`
- [x] 2.7 Verified that a call to `render_pdf(invoice)` with no `language` field still renders in English (with the intentional BeNeLux number-format change for every language including EN). All 4 languages render-tested end-to-end via the CLI and pdftotext verification

## 3. Webapp Form

- [x] 3.1 Added a `<select id="invoice-language">` next to the Currency field in `webapp/templates/index.html` with options EN / NL / FR / DE labeled in their own language (`English`, `Nederlands`, `Français`, `Deutsch`)
- [x] 3.2 Added a `<select id="default-language">` in the Settings modal's `field-row` alongside Currency and Due date offset, same four options
- [x] 3.3 Extended `DEFAULT_DEFAULTS` in `app.js` with `language: "en"` plus a `SUPPORTED_LANGUAGES` constant for validation when loading customer records. Wired through `getDefaults` / `saveDefaults` via the existing defaults helpers
- [x] 3.4 `applyDefaultsToForm()` sets `#invoice-language` from `getDefaults().language` on init, with the same "only if empty" guard used for `#currency` and `#payment_terms`
- [x] 3.5 `collectInvoice()` includes `language: ($("#invoice-language").value || "en").toLowerCase()` in the returned invoice dict
- [x] 3.6 `saveCustomer()` signature changed to `saveCustomer(buyer, language)` and stores `{...buyer, language}` on the customer record. `doSend()` passes `invoice.language` on the success path. The `#recent-customers` change handler destructures `{ language, ...buyer }` out of the loaded record, calls `setBuyer(buyer)` (which naturally ignores the extra `language` field because it only iterates `[data-buyer]` DOM inputs), and applies the language to `#invoice-language` if it's one of the supported codes
- [x] 3.7 `applyDefaultsToForm()` guard verified: it only sets `#invoice-language` if the field is empty. `clearInvoice()` (the "+" button handler) resets the language to the Settings default on a fresh start

## 4. CLI

- [x] 4.1 Added `--language` argument on `cli.py create` with `choices=["en", "nl", "fr", "de"]`, default `None`. When provided, `cmd_create` sets `data["language"] = args.language` before calling `generate_ubl()`, which threads through to `render_pdf` → `_build_view_model`

## 5. Tests

- [x] 5.1 `tests/test_i18n.py`: `t()` happy path — parametrized over all four supported languages, asserts every label key resolves to a non-empty string
- [x] 5.2 `tests/test_i18n.py`: `t()` fallback — unknown key returns the key name; unknown language returns the English string; unknown language + unknown key returns the key name; case-insensitive language codes (`"NL"` == `"nl"`)
- [x] 5.3 `tests/test_i18n.py`: **structural invariant** — `_TRANSLATIONS["nl"].keys() == _TRANSLATIONS["en"].keys()` (parametrized for fr/de). Guarantees no silent dict drift when new labels are added
- [x] 5.4 `tests/test_i18n.py`: `unit_label()` happy path + both fallback levels (unknown lang → EN; unknown code → raw code)
- [x] 5.5 `tests/test_i18n.py`: `unit_label()` structural invariant — every non-EN language covers every unit code in the EN set
- [x] 5.6 `tests/test_i18n.py`: `format_amount()` parametrized over 12 cases covering zero, 0.50, 99.99, 999.99, 1.000,00, 1.234,56, 12.345,67, 1.000.000,00, 1.234.567,89, negative numbers, and explicit rounding checks for `999.995` and `999.985` (ROUND_HALF_EVEN)
- [x] 5.7 `tests/test_pdf.py`: NL / FR / DE / EN view-model and rendered-HTML tests each asserting specific translated label strings (`Factuur`/`Omschrijving`/`uur` for NL, `Rechnung`/`Beschreibung`/`Stunde` for DE, etc.) — 9 new tests total
- [x] 5.8 `tests/test_pdf.py`: `test_view_model_unknown_language_falls_back_to_english` + `test_rendered_html_unknown_language_still_renders` — confirm no crash and EN fallback
- [x] 5.9 `tests/test_pdf.py`: updated 6 existing total-format assertions from ASCII (`"1000.00"`) to BeNeLux (`"1.000,00"`). The cross-check against UBL XML's `PayableAmount` now uses a `_parse_benelux` helper at the top of the test file to compare Decimals, since the XML stays ASCII
- [x] 5.10 `tests/test_epc_qr.py`: added `test_payload_amount_stays_ascii_regardless_of_language` — iterates all four languages and asserts `payload.split("\n")[7] == "EUR1234.56"`. EPC spec stays ASCII-locked
- [x] 5.11 Final sweep: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80` — all green, **178 tests passing**, coverage 99%, `i18n.py` at 100%

## 6. Docs

- [x] 6.1 `README.md`: added per-invoice PDF language support sentence to "What it does"; added a new webapp bullet describing the Language dropdown and customer-level persistence; added a `--language` CLI usage example in the command-line section
- [x] 6.2 `CLAUDE.md`: extended the `pdf.py` Architecture entry to mention the language/labels/unit_label/format_amount plumbing, and added a new entry for `peppol_sender/i18n.py` documenting the fallback rules and the structural-invariant test
- [x] 6.3 `docs/invoice-json-schema.md`: added the optional top-level `language` field to the Top-level fields table with allowed values (`en`/`nl`/`fr`/`de`), default (`en`), effect scope (PDF only, UBL XML and EPC QR payload unaffected), and unknown-code fallback behavior
