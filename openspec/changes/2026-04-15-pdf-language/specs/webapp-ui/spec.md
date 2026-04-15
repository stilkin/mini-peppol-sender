# Webapp UI

## MODIFIED Requirements

### Requirement: Per-invoice PDF language selection

The webapp MUST let the user choose the language of the generated PDF per invoice, with a cascade of defaults: the Settings modal stores a fallback `Default PDF language`, the saved-customer record persists a per-customer `language` field that auto-fills when the customer is loaded from the Recent dropdown, and the invoice form exposes a `Language` select next to the `Currency` field that the user can override at any time. The webapp UI itself is NOT translated — only the rendered PDF.

Supported languages: English (`en`), Dutch (`nl`), French (`fr`), German (`de`). Options in the UI select are labeled in their own language (`English`, `Nederlands`, `Français`, `Deutsch`).

#### Scenario: Settings default flows into new invoices

- **WHEN** the user sets `Default PDF language` to `nl` in the Settings modal, saves, and opens a fresh invoice form
- **THEN** the invoice form's `Language` select is pre-filled with `nl`, and `collectInvoice()` includes `language: "nl"` in the POST body to `/api/validate`, `/api/send`, and `/api/preview-pdf`

#### Scenario: Loaded customer auto-fills the language

- **WHEN** the user loads a saved customer from the Recent dropdown, and that customer's record has `language: "fr"`
- **THEN** the `Language` select changes to `fr`, overriding the Settings default for this invoice

#### Scenario: New customer inherits Settings default

- **WHEN** the user loads a saved customer from the Recent dropdown whose record does NOT have a `language` field (e.g. a customer saved before this feature shipped)
- **THEN** the `Language` select keeps whatever value it already has (does not clobber to Settings default), so the user sees the language they most recently worked in

#### Scenario: Manual override wins over cascade

- **WHEN** the user manually changes the `Language` select on the invoice form
- **THEN** the new value is used in `collectInvoice()` regardless of what the Settings default or loaded customer carried

#### Scenario: Language persists on the customer record at save

- **WHEN** the user sends an invoice successfully and `saveCustomer(buyer)` persists the buyer to localStorage
- **THEN** the persisted customer record includes the `language` field from the invoice form, so the next invoice to the same customer auto-fills correctly

#### Scenario: Language roundtrips through the invoice JSON

- **WHEN** any of `/api/validate`, `/api/send`, or `/api/preview-pdf` receives an invoice JSON body
- **THEN** the backend reads the top-level `language` field (if present) and passes it to `generate_ubl` / `render_pdf` unchanged, without any server-side cascade logic
