## 1. i18n Module

- [ ] 1.1 Create `peppol_sender/i18n.py` with module-level dicts: `_TRANSLATIONS` (lang → key → string) and `_UNIT_NAMES` (lang → unit code → name). Cover the four languages (EN, NL, FR, DE) for every key and every unit code in the existing `UNIT_CODES` list from `webapp/static/app.js`
- [ ] 1.2 Define the canonical label key set. At minimum: `invoice`, `from`, `bill_to`, `description`, `qty`, `unit`, `unit_price`, `line_total`, `subtotal`, `tax`, `total_due`, `payment`, `please_transfer_to`, `scan_with_banking_app`, `service_date`, `reference`, `vat`, `bic`, `issued`, `due`, `ref`
- [ ] 1.3 Implement `t(lang: str, key: str) -> str` with two-level fallback: requested language → English → key name. Case-insensitive on the language code
- [ ] 1.4 Implement `unit_label(lang: str, code: str) -> str` with two-level fallback: requested language → English → raw code
- [ ] 1.5 Implement `format_amount(value: Decimal) -> str` returning BeNeLux notation (`.` thousands, `,` decimals, always 2 decimal places). No language parameter — one canonical format for every PDF
- [ ] 1.6 Implement `all_labels(lang: str) -> dict[str, str]` as a convenience that builds the full labels dict for a given language, so `_build_view_model()` can hand the template a single object rather than calling `t()` per string
- [ ] 1.7 Draft the NL / FR / DE translations for all label keys and unit codes. Keep the register formal and commercial (how a small business would word a real invoice). Flag anything uncertain for the user's review

## 2. PDF Rendering Integration

- [ ] 2.1 Extend `peppol_sender/pdf.py`'s `_build_view_model()` to read `invoice.get("language", "en").lower()` and build `labels = i18n.all_labels(lang)`; attach `labels` to the view model
- [ ] 2.2 Within the display-lines loop, set `line["unit_label"] = i18n.unit_label(lang, raw_unit_code)` so the template can render the translated name
- [ ] 2.3 Replace the three formatted total strings (`subtotal`, `tax_total`, `grand_total`) with `i18n.format_amount(Decimal)` outputs (BeNeLux style). Line-level `unit_price` and `line_total` also use `format_amount` inside the display-lines loop
- [ ] 2.4 Confirm the amount string threaded into `build_epc_payload(invoice, grand_total_dec)` still uses the ASCII `EUR1234.56` format — the EPC payload is spec-locked and NOT localized. Only the PDF visual representation changes formatting
- [ ] 2.5 Update `peppol_sender/templates/invoice.html` to read every user-facing string from `{{ labels.<key> }}`. Replace hardcoded `Description`, `Qty`, `Unit`, `Unit price`, `Line total`, `Subtotal`, `Tax`, `Total due`, `From`, `Bill to`, `Payment`, `Please transfer to:`, `Scan with your banking app`, `Service date:`, `Reference:`, `BIC`, `VAT`, `Issued`, `Due`, `Ref`, `Invoice`
- [ ] 2.6 Update the line-items table in the template to render `{{ line.unit_label }}` instead of `{{ line.unit }}`
- [ ] 2.7 Verify that a call to `render_pdf(invoice)` with no `language` field still produces a byte-identical English PDF (up to the number-format change to BeNeLux, which is the intentional behavior change for EN as well)

## 3. Webapp Form

- [ ] 3.1 Add a `<select id="invoice-language">` next to the Currency field in `webapp/templates/index.html` with options EN / NL / FR / DE (labels in their own language for visual hinting: `English`, `Nederlands`, `Français`, `Deutsch`)
- [ ] 3.2 Add a `<select id="default-language">` in the Settings modal, next to the Default currency field, with the same four options
- [ ] 3.3 Extend `DEFAULT_DEFAULTS` in `app.js` with `language: "en"` and persist it through `getDefaults` / `saveDefaults` / the Settings modal's open/save helpers
- [ ] 3.4 On page init, set `#invoice-language` from `getDefaults().language`
- [ ] 3.5 In `collectInvoice()`, include `language: ($("#invoice-language").value || "en").toLowerCase()` in the returned invoice dict
- [ ] 3.6 Persist the language on the saved customer record: `saveCustomer(buyer)` should include the currently-selected `#invoice-language` value on the customer object alongside name/address. When a customer is loaded from the Recent dropdown, set `#invoice-language` to `customer.language` if present, otherwise leave the current selection alone
- [ ] 3.7 Confirm the `applyDefaultsToForm()` helper does NOT clobber a manually-set language — same guard pattern used for `#currency` and `#payment_terms` (only set if empty)

## 4. CLI

- [ ] 4.1 Add `--language` argument on `cli.py create` (choices: `en`, `nl`, `fr`, `de`), defaulting to `None`. When provided, override `invoice["language"]` before passing to `generate_ubl()`. When absent, use whatever the invoice JSON already has (or nothing, which means `_build_view_model` falls back to `"en"`)

## 5. Tests

- [ ] 5.1 `tests/test_i18n.py`: `t()` happy path — every label key resolves to a non-empty string in every supported language
- [ ] 5.2 `tests/test_i18n.py`: `t()` fallback — unknown key returns the key name; unknown language returns the English string; unknown language + unknown key returns the key name
- [ ] 5.3 `tests/test_i18n.py`: **structural invariant** — `_TRANSLATIONS["nl"].keys() == _TRANSLATIONS["en"].keys()` (and same for fr/de). Guarantees no silent dict drift when new labels are added
- [ ] 5.4 `tests/test_i18n.py`: `unit_label()` happy path + both fallback levels
- [ ] 5.5 `tests/test_i18n.py`: `unit_label()` structural invariant — every language covers every unit code in the shared `UNIT_CODES` set (or documents explicit exceptions)
- [ ] 5.6 `tests/test_i18n.py`: `format_amount()` covers zero, one decimal, two decimals, thousands, millions, values already at `.00`, values with rounding implications, and negative values. Asserts dot-thousands, comma-decimal, exactly two decimal places
- [ ] 5.7 `tests/test_pdf.py`: one test per language (EN/NL/FR/DE) asserting a known translated label string appears in the rendered HTML (e.g. `"Factuurnummer"` for NL, `"Beschreibung"` for DE, `"Description"` for FR, `"Description"` for EN)
- [ ] 5.8 `tests/test_pdf.py`: unknown language code (`"zz"`) falls back to English cleanly without raising
- [ ] 5.9 `tests/test_pdf.py`: `view_model["grand_total"]` for `SAMPLE_INVOICE` now reads `"1.000,00"` (BeNeLux) instead of `"1000.00"`. Other total-format tests updated to match. Confirm the total still equals `PayableAmount` from the UBL XML — the equality test must now parse the BeNeLux string back to compare with the ASCII UBL value, OR the cross-check should parse both to Decimal
- [ ] 5.10 `tests/test_epc_qr.py`: unchanged. Add one sanity assertion that `build_epc_payload` emits `EUR1000.00` (not `EUR1.000,00`) regardless of the invoice's `language` field — the EPC spec is ASCII-locked
- [ ] 5.11 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80` — all green

## 6. Docs

- [ ] 6.1 `README.md`: add one sentence under "What it does" mentioning per-invoice PDF language support for NL/EN/FR/DE. Add one webapp bullet describing the Language dropdown next to Currency and the Settings default
- [ ] 6.2 `CLAUDE.md`: add one Architecture-section entry for `peppol_sender/i18n.py` describing its role, fallback rules, and the structural invariant enforced by the test suite
- [ ] 6.3 `docs/invoice-json-schema.md`: document the new optional `language` top-level field (allowed values `en`/`nl`/`fr`/`de`, default `en`, effect on PDF rendering only)
