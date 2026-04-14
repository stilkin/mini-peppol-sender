## Context

The current generator has one gap that blocks real-world use: no `cac:PaymentMeans`. Users have been working around this by stuffing IBAN text into `PaymentTerms/Note` — structurally this transmits, but receivers' bookkeeping software ignores it because IBAN belongs in `PayeeFinancialAccount/ID`, not a free-form note. Rule BR-50 also makes it non-compliant the moment the payment means code is credit transfer (which it always is for an invoice-for-payment).

The fix is small: add a PaymentMeans builder, insert it in the correct UBL sequence slot, add a local validator rule, and surface IBAN/BIC fields in the webapp Settings modal. No new dependencies, no new modules.

## Goals / Non-Goals

**Goals:**

- Emit compliant `cac:PaymentMeans` whenever the invoice dict contains a `payment_means` block.
- Default `PaymentMeansCode` to `30` (UNCL4461 credit transfer) — the 95% case.
- Default `payment_id` to the invoice number and `account_name` to the seller name so callers can supply just the IBAN and get a correct output.
- Local BR-50 check in `validate_basic` that mirrors the Peppyrus server-side rule.
- Webapp Settings modal gains persistent IBAN / BIC / account holder fields.

**Non-Goals:**

- Direct debit (code `49`) and SEPA direct debit mandates (`PaymentMandate`). Credit transfer only for now.
- Prepaid payments (`cac:PrepaidPayment`).
- Multiple bank accounts per seller or per invoice.
- Client-side IBAN format validation — leave that to the receiver / Peppyrus. We only check presence.
- Any CLI flag surface change: the JSON drives the output.

## Decisions

**Bank details stored as a per-seller default, not per-invoice input**

- IBAN rarely changes for a given business. The webapp's existing Settings modal pattern (currency, payment terms, due-date offset, default tax category) already holds per-seller defaults in localStorage; bank details fit the same pattern.
- Alternative considered: per-invoice input field — rejected as unnecessary friction for the common case. Advanced users who need per-invoice bank details can still set `payment_means` directly in the JSON.

**Default `PaymentMeansCode` = `30`**

- UNCL4461 code `30` ("credit transfer") is the BIS Billing 3.0 canonical value. Code `58` ("SEPA credit transfer") is also allowed and receivers handle both identically; `30` is the safer interop default.
- Overridable via `payment_means.code`.

**Sensible defaults for `account_name` and `payment_id`**

- `account_name` defaults to the seller name. Most small businesses use a personal/company account whose holder matches the seller name.
- `payment_id` defaults to the invoice number, giving the buyer a ready-made remittance reference that the seller can reconcile against.

**BR-50 as a local FATAL rule (`LOCAL-BR-50`)**

- Check: if `PaymentMeansCode` is `30` or `58`, `PayeeFinancialAccount/ID` must be non-empty. Otherwise emit a FATAL rule.
- Rule ID `LOCAL-BR-50` mirrors the Peppyrus server-side rule name so users can correlate local and remote validation output.
- Runs in `validate_basic`, not `validate_xsd` — the XSD permits an absent PaymentMeans; BR-50 is a business rule, not a structural one.

**PaymentTerms/Note stays for free-form notes**

- "Net 21 days", "Late payment penalty 8%", etc. still belong there. The webapp just removes the misleading IBAN placeholder so users stop putting bank details in the wrong field.

**JSON shape**

```json
"payment_means": {
  "code": "30",
  "iban": "BE00000000000000",
  "bic": "BANKBEBB",
  "account_name": "Seller Name",
  "payment_id": "INV-0001"
}
```

- Whole block is optional at the JSON level; if omitted, no `cac:PaymentMeans` is emitted and `LOCAL-BR-50` does not fire. This keeps existing tests green without forced migration.
- Once emitted, BR-50 applies. That's the correct behaviour.

## Risks / Trade-offs

- **Backwards compatibility**: existing `sample_invoice.json` and tests don't set `payment_means`. They remain valid (no PaymentMeans emitted, no BR-50 triggered). We'll update `sample_invoice.json` to include a realistic bank account so the default CLI flow produces a compliant invoice end-to-end.
- **Users who currently put IBAN in `PaymentTerms/Note`**: their invoices still transmit. Receivers will see both a structured `PaymentMeans` block (once they adopt this change) and the free-form note. That's harmless — bookkeeping software reads the structured one.
- **BR-50 rule accuracy**: the rule only checks `PaymentMeansCode` in `{30, 58}`. Other codes (cash `10`, cheque `20`, direct debit `49`) don't require an IBAN and should not trigger the rule. Tested explicitly.
- **Concurrency with credit-note change**: this change and the proposed `2026-04-14-credit-note-support` change both touch `peppol_sender/ubl.py`. Whichever lands first, the second rebases by inserting its helper call into `_build_document` (post-credit-note refactor) or directly into `generate_ubl` (pre-refactor). No structural conflict.
