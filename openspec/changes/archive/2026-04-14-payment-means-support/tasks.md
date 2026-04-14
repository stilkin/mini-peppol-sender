## 1. UBL Generator

- [x] 1.1 Add `_add_payment_means(parent, data, currency)` helper in `peppol_sender/ubl.py` that emits `cac:PaymentMeans` with `PaymentMeansCode`, optional `PaymentID`, and `PayeeFinancialAccount` (ID, optional Name, optional `FinancialInstitutionBranch/ID` for BIC)
- [x] 1.2 Call `_add_payment_means()` in the document builder, positioned between `AccountingCustomerParty` and the `PaymentTerms` block (correct UBL `xs:sequence` position)
- [x] 1.3 Apply defaults: `code` → `"30"`, `account_name` → seller name, `payment_id` → invoice number; omit the whole block if `payment_means` is absent from the invoice dict

## 2. Validator — BR-50 local check

- [x] 2.1 Add a BR-50 check in `validate_basic()`: if the XML contains `PaymentMeansCode` in `{"30", "58"}` and no non-empty `PayeeFinancialAccount/ID`, return a FATAL rule with `id: LOCAL-BR-50`, location pointing to the PaymentMeans element
- [x] 2.2 Ensure BR-50 does not fire for other codes (`10`, `20`, `49`, etc.) or when no PaymentMeans is emitted at all

## 3. Webapp

- [x] 3.1 Add IBAN, BIC, and account-holder-name fields to the Settings modal in `webapp/templates/index.html`, matching the existing form styling
- [x] 3.2 Persist the new fields in localStorage under the existing seller-defaults key; load them on page init
- [x] 3.3 Include the new fields in the JSON payloads POSTed to `/api/validate` and `/api/send` (map to the `payment_means` block)
- [x] 3.4 Remove the misleading `IBAN: BE00 0000 0000 0000` placeholder from the `PaymentTerms` textarea

## 4. Tests

- [x] 4.1 `tests/test_ubl.py`: assert `cac:PaymentMeans` structure, default `code`, BIC handling, `payment_id` fallback, correct UBL sequence position
- [x] 4.2 `tests/test_validator.py`: BR-50 triggers when IBAN missing for code 30/58; passes when IBAN present; does not fire for cash/cheque codes; does not fire when PaymentMeans is absent
- [x] 4.3 `tests/test_webapp.py`: Settings payload persisted and echoed through the validate/send routes; validate route returns `LOCAL-BR-50` when IBAN is missing
- [x] 4.4 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest --cov-fail-under=80`

## 5. Docs and Samples

- [x] 5.1 Update `sample_invoice.json` with a realistic `payment_means` block so `cli.py create` produces a BR-50-compliant invoice out of the box
- [x] 5.2 Update `docs/invoice-json-schema.md` with the `payment_means` field reference and defaults
- [x] 5.3 Update `README.md`: note that bank details live in `payment_means`, not `PaymentTerms`
