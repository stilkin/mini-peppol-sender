# PDF Rendering

## MODIFIED Requirements

### Requirement: Translated PDF output per invoice language

The rendered PDF MUST use localized user-facing strings chosen by the invoice's `language` field. Supported languages are English (`en`), Dutch (`nl`), French (`fr`), and German (`de`). An invoice without a `language` field, or with an unrecognized code, renders in English.

Translation MUST be implemented in a dedicated pure module `peppol_sender/i18n.py` exposing `t(lang, key) -> str`, `unit_label(lang, code) -> str`, `format_amount(value: Decimal) -> str`, and `all_labels(lang) -> dict[str, str]`. The module MUST NOT introduce a runtime dependency; translations live in hand-rolled Python dicts. Lookups MUST fall back to English on missing keys, and to the raw key/code when even English is missing.

Monetary amounts in the PDF MUST be formatted in BeNeLux notation (`.` as thousands separator, `,` as decimal separator, always two decimal places) regardless of the selected language. The EPC QR payload is independent of this requirement and continues to emit ASCII `EUR<amount>` per EPC069-12.

Dates in the PDF MUST remain in ISO format (`YYYY-MM-DD`) regardless of the selected language.

#### Scenario: Dutch invoice shows Dutch labels

- **WHEN** an invoice with `language: "nl"` is rendered
- **THEN** the PDF's user-facing labels appear in Dutch (e.g. `Factuurnummer`, `Beschrijving`, `Aantal`, `Eenheid`, `Eenheidsprijs`, `Totaal`, `Subtotaal`, `Belasting`, `Te betalen`)

#### Scenario: English invoice unchanged (except number format)

- **WHEN** an invoice with `language: "en"` (or no `language` field) is rendered
- **THEN** labels appear in English (`Description`, `Qty`, `Unit`, etc.) and the PDF is byte-identical to the pre-translation version of the tool, except that monetary amounts switch to BeNeLux notation (e.g. `1.000,00` instead of `1000.00`)

#### Scenario: Unknown language falls back to English

- **WHEN** an invoice with `language: "zz"` (or any code not in the supported set) is rendered
- **THEN** the PDF renders using English labels and unit names without raising an error

#### Scenario: Unit codes render as translated names

- **WHEN** a line item uses unit code `HUR` and the invoice `language` is `nl`
- **THEN** the PDF's line-items table displays `uur` in the unit column, not `HUR`

#### Scenario: Unknown unit codes render as the raw code

- **WHEN** a line item uses a unit code not present in the unit-name dict (e.g. a code outside the `UNIT_CODES` set)
- **THEN** the PDF falls back to displaying the raw code so the output never breaks

#### Scenario: BeNeLux number formatting for all languages

- **WHEN** an invoice with any supported language renders a line total of `1234.56`
- **THEN** the PDF displays `1.234,56` (dot thousands, comma decimals) regardless of the language

#### Scenario: EPC QR payload stays ASCII

- **WHEN** an invoice with `language: "nl"` (or `fr`/`de`) is rendered and has a valid EUR credit-transfer payment means
- **THEN** the embedded EPC QR payload's amount field reads `EUR1234.56` (ASCII), not `EUR1.234,56` — the EPC spec is independent of PDF display language

#### Scenario: Translation dict structural invariant

- **WHEN** the test suite runs
- **THEN** every supported non-English language has the same label key set as English, asserted by a test in `tests/test_i18n.py`, so that no label can be added to the PDF template without translations being provided in every supported language
