## Context

Peppify's current PDF template is hardcoded English. Line items render raw UN/ECE unit codes (`HUR`, `C62`, `MTK`) from the `UNIT_CODES` list in `webapp/static/app.js` — correct for structured UBL but unreadable as a human invoice. Monetary amounts use the ASCII format `1000.00` via Python's `f"{grand_total:.2f}"`, which is legible but reads as imported-from-a-spreadsheet in BeNeLux where `1.000,00` is the norm.

Four target languages cover the practical operating region: Dutch, English, French, German. Further languages can be added later by extending the dicts; the infrastructure does not need to know them up front.

The change is surgically scoped to the PDF-rendering path. The UBL XML sent to PEPPOL remains language-agnostic (it's machine-read, not human-read; receivers' accounting software translates the structured fields to their own UI language). The EPC QR payload is also unchanged — IBAN, amount, and reference are not translated, they're bank-routing data.

The decision to stay PDF-only (not translate the webapp UI) is load-bearing for scope control. See Non-Goals.

## Goals / Non-Goals

**Goals:**

- Translate every user-facing string on the PDF into the invoice's chosen language (EN / NL / FR / DE).
- Replace opaque unit codes (`HUR`, `C62`, …) with readable names (`uur`, `stuk`, …) in the line-items table.
- Format monetary amounts in BeNeLux notation (`1.234,56 EUR`) regardless of the PDF language — one canonical format, not per-locale.
- Keep dates in ISO (`2026-04-15`) — universal, unambiguous, zero translation work.
- Cascade language selection: Settings default → Customer record → Per-invoice override. A freshly-installed Peppify uses English; setting a Settings default makes new invoices default to that; loading a saved customer uses their remembered language; manual override on the invoice form wins.
- Ship the four translation dictionaries as hand-drafted content, reviewed by the user before merge.
- Degrade gracefully: an invoice with no `language` field, or with a language code we don't recognize, silently renders in English.

**Non-Goals:**

- Translating the webapp UI. Operator-facing tool, single user, maintenance cost doubles for every new feature. See Decisions for rationale.
- Per-locale date formatting. ISO is universal; translating month names triples the data surface for minor cosmetic gain.
- Per-locale number formatting (i.e. English invoices still getting `1.234,56`). We use BeNeLux notation for every language because the target market is BeNeLux, the user explicitly asked for it, and the simplification is worth more than the minor jarring for an English recipient.
- Locale-aware currency symbol placement (`€1,234.56` vs `1.234,56 €`). The current `120.00 EUR` format stays — ISO code as space-separated suffix — because it's unambiguous in every language.
- Right-to-left language support.
- Plural forms. None of the labels we translate have plural-dependent grammar.
- A translation framework like Babel / gettext / Fluent. Overkill for ~50 strings × 4 languages; a hand-rolled dict with English fallback is all we need.
- Automated round-trip translation testing against a reference file. The four translation dicts are reviewed by the user at merge time and treated as content, not tested for accuracy beyond structural invariants (all keys present in all languages).
- Translating tax category names (`Standard rate`, `Exempt`, …). They are never displayed in the PDF — only the structured UBL carries them.
- Translating validation rule messages (`BR-50`, `LOCAL-F001`, …). These come from `validator.py`, surface in the webapp (operator-facing), and are out of scope per the UI-stays-English decision.

## Decisions

**Hand-rolled dicts, not Babel**

- No new runtime dependency. `i18n.py` is ~150 LOC including all 4 × ~20-key label dicts and the 4 × 16-entry unit-name dicts.
- Lookups are three pure functions: `t(lang, key)`, `unit_label(lang, code)`, `format_amount(value)`. Each handles its own fallback and is trivially unit-testable.
- Babel would give us locale-aware date/number formatting "for free", but we deliberately chose ISO dates and BeNeLux numbers — so the free stuff isn't needed, and the dependency cost (substantial wheel, optional C extensions on some platforms) is pure overhead.
- **Alternative rejected**: `gettext` with `.po` files. Standard in larger projects but requires a compile step (`msgfmt`), a build-time toolchain, and introduces file-format tooling that three people on a BeNeLux SMB team will forget how to use within a month. Python dicts edited in place are self-documenting.
- **Alternative rejected**: Fluent (Mozilla's successor to gettext). Same argument, more exotic tooling.

**Language cascade: Settings → Customer → Invoice**

- Users with a multilingual customer base flip between languages per invoice, not per session. A global "UI language" setting would force a Settings round-trip every time you invoice a different customer — friction on a per-invoice action.
- Storing the language on the saved-customer record means: first invoice to a Dutch customer, you pick NL once; every subsequent invoice to that customer auto-fills NL without thinking.
- The per-invoice dropdown is always present as an override — you can still bill an existing customer in a different language if you need to.
- The Settings default is the fallback when neither customer nor manual choice is set. First-run experience in a fresh browser: invoices default to EN until you change the Settings default.
- The cascade is computed at form-display time, not at send time. The invoice JSON stores the final resolved language as a flat `language` field — the backend doesn't know about the cascade.

**Dates stay ISO, numbers go BeNeLux**

- ISO dates (`2026-04-15`) are universal, unambiguous, and already machine-correct in the underlying UBL. Localizing them would require translating all 12 month names × 4 languages (48 strings of content to maintain) for purely cosmetic gain. A layperson reading an invoice can parse `2026-04-15` at a glance.
- Numbers are the opposite — `1.000,00` is actively expected in BeNeLux, and `1,000.00` reads as sloppy or foreign on an invoice. One canonical BeNeLux format, one helper function, no per-locale branching.
- Trade-off accepted: an English-speaking customer outside BeNeLux gets an English-translated PDF with BeNeLux number formatting. They'll notice but won't be confused.

**Unit codes translated in the view model, not in the template**

- The `display_lines` list in `_build_view_model()` gets a new `unit_label` key alongside the existing `unit` key. The template reads `line.unit_label`, the structured UBL generator (`ubl.py`) still emits the raw code.
- This keeps the structured XML and the human-readable PDF cleanly decoupled: the UBL is language-agnostic, the PDF is one of four languages.
- It also makes the fallback behavior explicit: if an unknown unit code shows up, `unit_label()` returns the code itself, so the PDF never breaks — it just shows the code the way the current English version does.

**Labels as a dict in the view model, not as a Jinja `{% trans %}` filter**

- Jinja has third-party i18n extensions. We're deliberately not installing them.
- Building a flat `labels = {...}` dict once in Python and reading `{{ labels.description }}` in the template keeps all translation lookups in one place (`_build_view_model()`), and the template stays logic-free as required by the existing `pdf-rendering` spec.

**English fallback on every lookup**

- `t("de", "unknown_key")` → tries `_TRANSLATIONS["de"]["unknown_key"]`, falls back to `_TRANSLATIONS["en"]["unknown_key"]`, falls back to the key itself.
- Same rule for `unit_label()`: unknown language OR unknown code → English name → raw code.
- Guarantees the PDF never crashes or renders partial strings. Missing translations look like English text, which is better than a broken layout or a `KeyError` at render time.

**Language code format: BCP-47 lowercase (`"en"`, `"nl"`, `"fr"`, `"de"`)**

- Two-letter lowercase, matching ISO 639-1. No `fr-BE` / `nl-BE` region variants — we don't have content that differs between BeNeLux French and France French, or between Flemish Dutch and Dutch Dutch.
- Future region-specific overrides are an easy extension if they ever become necessary (add `"fr-be"` as a second-tier lookup, fall back to `"fr"`).

**No new routes on the webapp backend**

- The language choice rides inside the existing invoice JSON on `POST /api/validate`, `POST /api/send`, and `POST /api/preview-pdf`. Backend treats it as one more optional field.
- `/api/preview-pdf` automatically honors it because `render_pdf` re-uses `_build_view_model`.
- The Settings modal writes to the existing `peppol_defaults` localStorage key (under a new `language` sub-key).

## Risks / Trade-offs

- **Translation accuracy**: initial translations are drafted by Claude and reviewed by the user. Moderate-confidence vocabulary for NL/FR/DE professional invoice terms exists in the training data, but "is this the right word for a formal commercial invoice in Flemish Dutch" is a judgment call the user has to make. Mitigation: the user is fluent in all four languages and will review every string before merge.
- **BeNeLux number format feels foreign to non-EU recipients**: if a Peppify user ever sends an English invoice to a US customer, `1.234,56 EUR` will look wrong. Accepted trade-off — the user explicitly asked for BeNeLux-only, and Peppify's positioning is a BeNeLux tool.
- **Translation dict bitrot**: every new label added to the PDF template becomes a synchronization point across four languages. Mitigation: a small structural test in `test_i18n.py` that asserts every non-EN language has the same key set as EN (fails at CI if someone adds `labels.new_key` in English but forgets to add it to NL/FR/DE).
- **UI / PDF language mismatch**: the webapp UI is English, the PDF is (potentially) Dutch. A user composing a Dutch invoice sees "Invoice number" in English on the form and "Factuurnummer" on the rendered PDF. Mild cognitive friction, but users routinely flip between "editor language" and "output language" in real-world tools (IDE in English, code comments in native language, etc.). Acceptable; reconsider if user feedback says otherwise.
- **Settings cascade complexity**: three levels (default → customer → invoice) is more state than two. Mitigation: the cascade lives entirely in the frontend (`app.js`); the backend receives a single resolved `language` string. Backend testing stays simple.
- **Future-proofing vs YAGNI**: the temptation is to build a generic i18n layer that can scale to 20 languages. We explicitly don't. If a fifth language is ever needed, adding a new inner dict is one copy-paste; if 20 languages become a real need, we'll know by then whether `.po` files become worth the ceremony.
