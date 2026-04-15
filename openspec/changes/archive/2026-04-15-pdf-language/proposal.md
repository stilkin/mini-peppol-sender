## Why

Peppify's PDF is customer-facing — recipients see it in their bank app, their accounting software, or on paper. Today every PDF is rendered in English with opaque UN/ECE unit codes (`HUR`, `C62`, `MTK`) that a layperson cannot read. A Belgian SMB that invoices a mix of Dutch, English, French, and German-speaking customers has to either ship all recipients an English invoice that looks foreign, or compose one manually outside the tool. Neither is acceptable for a production invoicing tool.

Translating the PDF — labels, unit names, and number formatting — makes the customer-facing output feel native to the recipient without adding backend complexity. It's also the change with the highest customer-facing value per line of code in the codebase, because the recipient reads every word.

## What Changes

- Add a new module `peppol_sender/i18n.py` holding translation dictionaries for four languages (EN, NL, FR, DE) and a small set of pure lookup helpers: `t(lang, key)`, `unit_label(lang, code)`, `format_amount(value)`. No new runtime dependency — hand-rolled Python dicts, one lookup function per concern, English fallback on missing keys.
- Extend `peppol_sender/pdf.py`'s `_build_view_model()` to read a new optional `language` field on the invoice dict (default `"en"`), build a `labels` sub-dict of translated PDF strings from `i18n.t`, replace each line's raw unit code with its translated `unit_label`, and format all monetary amounts in BeNeLux notation (`1.234,56`) regardless of language.
- Update `peppol_sender/templates/invoice.html` to read every user-facing string from `labels.*` instead of hardcoding English, and to render `line.unit_label` instead of `line.unit`.
- Extend the webapp: add a `Language` dropdown next to the Currency field, a `Default PDF language` select in the Settings modal, and persist the chosen language on the saved-customer record so loading a recent customer auto-fills it.
- Extend the CLI: add a `--language` flag on `create` defaulting to the value in the invoice JSON or `"en"`.
- Dates stay in ISO (`2026-04-15`) — deliberately **not** localized. Universal, unambiguous, no month-name translation needed.
- Numbers switch to BeNeLux notation (`1.234,56 EUR`) globally — simpler than per-locale separators and matches the target market.
- The UI itself stays in English. Webapp strings, error messages, and validation rules are not translated in this change.

## Capabilities

### Modified Capabilities

- `pdf-rendering`: View model builds translated labels from the invoice's `language` field and swaps raw unit codes for human-readable unit names. Number formatting switches from ASCII decimal to BeNeLux style.
- `webapp-ui`: A new `Language` dropdown sits next to Currency in the invoice form; a new `Default PDF language` select in the Settings modal; saved customers persist a `language` field and auto-fill it on recall.

## Impact

- **New files**: `peppol_sender/i18n.py`, `tests/test_i18n.py`.
- `peppol_sender/pdf.py`: ~15 LOC added in `_build_view_model()` — read language, build labels, translate line unit codes, reformat amounts via `i18n.format_amount()`.
- `peppol_sender/templates/invoice.html`: ~15 label-text replacements (`Description` → `{{ labels.description }}`, etc.), line table renders `line.unit_label` instead of `line.unit`, totals use the new BeNeLux-formatted strings.
- `webapp/templates/index.html`: 1 `<select id="invoice-language">` next to the Currency field, 1 `<select id="default-language">` in the Settings modal.
- `webapp/static/app.js`: default language wired into `getDefaults` / `saveDefaults` / `applyDefaultsToForm`; customer save/load round-trips the language field; invoice form dropdown feeds `collectInvoice()`; ~25 LOC.
- `cli.py`: `--language` argument on `create`, threaded into `generate_ubl` as part of the invoice dict.
- `tests/test_i18n.py` (new): key lookup, fallback to English on missing key, all four languages × a sample of keys, unit-label lookups, BeNeLux amount formatting edge cases (zero, thousands, millions, negative).
- `tests/test_pdf.py`: one positive-path test per language confirming a known label string appears in the rendered HTML; one fallback test for an unsupported language code.
- `README.md`: one paragraph in "What it does" and one line in the webapp feature list.
- `CLAUDE.md`: one entry in the Architecture section for `i18n.py`.
- `docs/invoice-json-schema.md`: one new optional top-level `language` field documented with allowed values and default.
- **Not touched**: `peppol_sender/ubl.py` (UBL XML is language-agnostic), `peppol_sender/validator.py`, `peppol_sender/api.py`, `peppol_sender/epc_qr.py` (EPC payload is language-independent — IBAN / amount / reference don't translate), `schemas/`, any other OpenSpec capability.
