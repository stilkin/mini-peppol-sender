## Why

The generator emits no `cac:PaymentMeans` element at all. The only place bank account info can currently land is free text inside `PaymentTerms/Note` — the webapp template even suggests this with a placeholder ("IBAN: BE00 0000 0000 0000" in `webapp/templates/index.html:135`). Receivers' accountancy software reads structured `cac:PaymentMeans`, not free-form notes, so today's invoices cannot be auto-processed by the receiver's bookkeeping tools.

More critically: PEPPOL BIS Billing 3.0 rule **BR-50** requires a structured IBAN whenever `PaymentMeansCode` is `30` or `58` (credit transfer). Every invoice intended to be paid by bank transfer — i.e. every invoice this tool generates — is non-compliant the moment it leaves. Peppyrus catches this server-side, but there's no reason to defer; shift-left validation is trivial.

## What Changes

- Add `_add_payment_means()` helper to `peppol_sender/ubl.py`. Emit `<cac:PaymentMeans>` between `AccountingCustomerParty` and `PaymentTerms` in the UBL sequence.
- Extend the invoice JSON schema with an optional `payment_means` block: `code` (default `30`), `iban`, `bic` (optional), `account_name` (defaults to seller name), `payment_id` (defaults to invoice number).
- Add a local BR-50 check to `validate_basic()`: if `PaymentMeansCode` is `30` or `58` and `PayeeFinancialAccount/ID` is missing or empty, return a FATAL rule with `id: LOCAL-BR-50`.
- Webapp: add IBAN / BIC / account holder fields to the Settings modal (per-seller defaults stored in localStorage, matching the existing currency / payment terms / due date offset pattern). Remove the now-misleading "IBAN: BE00 ..." placeholder from the `PaymentTerms` textarea.
- Update `sample_invoice.json`, `docs/invoice-json-schema.md`, and tests.

## Capabilities

### Modified Capabilities

- `ubl-generation`: Emit structured `cac:PaymentMeans` with IBAN, BIC, payment ID, and credit-transfer code defaulting to `30`.
- `invoice-validation`: Local BR-50 check shifts server-side rule left into the CLI / webapp flow.
- `webapp-ui`: Bank account fields live in the Settings modal alongside other seller defaults.

## Impact

- `peppol_sender/ubl.py`: New helper, new call site in `generate_ubl()` / (post-credit-note) `_build_document`.
- `peppol_sender/validator.py`: New BR-50 check branch.
- `webapp/templates/index.html`: Settings modal gains three fields; PaymentTerms placeholder removed.
- `webapp/static/app.js`: Load/save bank-account settings, include in `/api/validate` and `/api/send` payloads.
- `tests/test_ubl.py`, `tests/test_validator.py`, `tests/test_webapp.py`: New coverage.
- `sample_invoice.json`: Add a `payment_means` block.
- `docs/invoice-json-schema.md`, `README.md`: Document the new field; note that `PaymentTerms/Note` is for free-form notes only, not bank details.
- **Not touched**: `peppol_sender/api.py`, `cli.py` (no flag surface change — the JSON drives the output).
