"""Hand-rolled translation dictionaries and lookup helpers for the PDF.

Supports EN / NL / FR / DE. The PDF is the only layer that consumes this —
the webapp UI, validator messages, CLI output, and UBL XML all stay English
by design. See openspec/changes/archive/2026-04-15-pdf-language/design.md for
the rationale.

Three concerns, three pure functions, English fallback on every lookup:
- `t(lang, key)` — label string
- `unit_label(lang, code)` — human-readable name for a UN/ECE unit code
- `format_amount(value)` — BeNeLux monetary format (`1.234,56`, language-independent)

Plus `all_labels(lang)` as a convenience for building a template context.

Adding a new language: extend `_TRANSLATIONS` and `_UNIT_NAMES` with the same
key set as English. `test_i18n.py` enforces this structurally — adding one
key to English without adding it to every other language will fail CI.
"""

from collections.abc import Mapping
from decimal import Decimal

# French typographic convention: non-breaking space before : ! ? ; »
# We use the explicit \u00a0 escape in source so the NBSP is visible to
# future maintainers and doesn't get silently collapsed by editors.
_NBSP = "\u00a0"

_TRANSLATIONS: Mapping[str, Mapping[str, str]] = {
    "en": {
        "invoice": "Invoice",
        "credit_note": "Credit Note",
        "from": "From",
        "bill_to": "Bill to",
        "description": "Description",
        "qty": "Qty",
        "unit": "Unit",
        "unit_price": "Unit price",
        "line_total": "Line total",
        "subtotal": "Subtotal",
        "tax": "Tax",
        "total_due": "Total due",
        "payment": "Payment",
        "please_transfer_to": "Please transfer to:",
        "scan_with_banking_app": "Scan with your banking app",
        "service_date": "Service date:",
        "reference": "Reference:",
        "vat": "VAT",
        "bic": "BIC",
        "issued": "Issued",
        "due": "Due",
        "ref": "Ref",
    },
    "nl": {
        "invoice": "Factuur",
        "credit_note": "Creditnota",
        "from": "Van",
        "bill_to": "Aan",
        "description": "Omschrijving",
        "qty": "Aantal",
        "unit": "Eenheid",
        "unit_price": "Prijs per eenheid",
        "line_total": "Totaal",
        "subtotal": "Subtotaal",
        "tax": "Btw",
        "total_due": "Te betalen",
        "payment": "Betaling",
        "please_transfer_to": "Gelieve over te schrijven naar:",
        "scan_with_banking_app": "Scan met uw bankapp",
        "service_date": "Prestatiedatum:",
        "reference": "Mededeling:",
        "vat": "Btw-nr.",
        "bic": "BIC",
        "issued": "Opgesteld",
        "due": "Vervaldatum",
        "ref": "Ref.",
    },
    "fr": {
        "invoice": "Facture",
        "credit_note": "Note de crédit",
        "from": "De",
        "bill_to": "À",
        "description": "Description",
        "qty": "Qté",
        "unit": "Unité",
        "unit_price": "Prix unitaire",
        "line_total": "Total",
        "subtotal": "Sous-total",
        "tax": "TVA",
        "total_due": "Total à payer",
        "payment": "Paiement",
        "please_transfer_to": f"Veuillez effectuer le virement sur{_NBSP}:",
        "scan_with_banking_app": "Scannez avec votre app bancaire",
        "service_date": f"Date de prestation{_NBSP}:",
        "reference": f"Communication{_NBSP}:",
        "vat": "N° TVA",
        "bic": "BIC",
        "issued": "Émise le",
        "due": "Échéance",
        "ref": "Réf.",
    },
    "de": {
        "invoice": "Rechnung",
        "credit_note": "Gutschrift",
        "from": "Von",
        "bill_to": "An",
        "description": "Beschreibung",
        "qty": "Menge",
        "unit": "Einheit",
        "unit_price": "Einzelpreis",
        "line_total": "Gesamtpreis",
        "subtotal": "Zwischensumme",
        "tax": "MwSt.",
        "total_due": "Gesamtbetrag",
        "payment": "Zahlung",
        "please_transfer_to": "Bitte überweisen an:",
        "scan_with_banking_app": "Mit Banking-App scannen",
        "service_date": "Leistungsdatum:",
        "reference": "Verwendungszweck:",
        "vat": "USt-IdNr.",
        "bic": "BIC",
        "issued": "Ausgestellt",
        "due": "Fällig",
        "ref": "Ref.",
    },
}

# UN/ECE Rec 20 unit codes — translated to human-readable names per language.
# Mirrors the `UNIT_CODES` list in webapp/static/app.js.
_UNIT_NAMES: Mapping[str, Mapping[str, str]] = {
    "en": {
        "EA": "each",
        "C62": "piece",
        "HUR": "hour",
        "MIN": "minute",
        "DAY": "day",
        "WEE": "week",
        "MON": "month",
        "ANN": "year",
        "KGM": "kilogram",
        "GRM": "gram",
        "LTR": "litre",
        "MTR": "metre",
        "MTK": "sq m",
        "MTQ": "cu m",
        "KMT": "km",
        "KWH": "kWh",
    },
    "nl": {
        "EA": "stuk",
        "C62": "stuk",
        "HUR": "uur",
        "MIN": "minuut",
        "DAY": "dag",
        "WEE": "week",
        "MON": "maand",
        "ANN": "jaar",
        "KGM": "kilogram",
        "GRM": "gram",
        "LTR": "liter",
        "MTR": "meter",
        "MTK": "m²",
        "MTQ": "m³",
        "KMT": "km",
        "KWH": "kWh",
    },
    "fr": {
        "EA": "unité",
        "C62": "pièce",
        "HUR": "heure",
        "MIN": "minute",
        "DAY": "jour",
        "WEE": "semaine",
        "MON": "mois",
        "ANN": "année",
        "KGM": "kilogramme",
        "GRM": "gramme",
        "LTR": "litre",
        "MTR": "mètre",
        "MTK": "m²",
        "MTQ": "m³",
        "KMT": "km",
        "KWH": "kWh",
    },
    "de": {
        "EA": "Stück",
        "C62": "Stück",
        "HUR": "Stunde",
        "MIN": "Minute",
        "DAY": "Tag",
        "WEE": "Woche",
        "MON": "Monat",
        "ANN": "Jahr",
        "KGM": "Kilogramm",
        "GRM": "Gramm",
        "LTR": "Liter",
        "MTR": "Meter",
        "MTK": "m²",
        "MTQ": "m³",
        "KMT": "km",
        "KWH": "kWh",
    },
}


def _normalize_lang(lang: str) -> str:
    return (lang or "").lower()


def t(lang: str, key: str) -> str:
    """Look up a label string. Falls back to English, then to the key itself."""
    code = _normalize_lang(lang)
    value = _TRANSLATIONS.get(code, {}).get(key)
    if value is not None:
        return value
    return _TRANSLATIONS["en"].get(key, key)


def unit_label(lang: str, code: str) -> str:
    """Look up a unit-code name. Falls back to English, then to the raw code."""
    lc = _normalize_lang(lang)
    value = _UNIT_NAMES.get(lc, {}).get(code)
    if value is not None:
        return value
    return _UNIT_NAMES["en"].get(code, code)


def all_labels(lang: str) -> dict[str, str]:
    """Return the full labels dict for a given language, with English fallback
    applied per-key so the caller can hand the template one complete object."""
    code = _normalize_lang(lang)
    en = _TRANSLATIONS["en"]
    src = _TRANSLATIONS.get(code, {})
    result: dict[str, str] = {}
    for key in en:
        value = src.get(key)
        result[key] = value if value is not None else en[key]
    return result


def format_amount(value: Decimal) -> str:
    """Format a monetary Decimal in BeNeLux notation.

    Dot as thousands separator, comma as decimal separator, always two decimal
    places. Deliberately language-independent — every Peppify PDF uses this
    format regardless of the selected language, matching the target market.

    Examples:
        Decimal("0")        -> "0,00"
        Decimal("0.5")      -> "0,50"
        Decimal("1234.56")  -> "1.234,56"
        Decimal("1000000")  -> "1.000.000,00"
        Decimal("-1234.56") -> "-1.234,56"
    """
    q = value.quantize(Decimal("0.01"))
    sign = "-" if q < 0 else ""
    int_part, dec_part = str(abs(q)).split(".")
    grouped = ""
    while len(int_part) > 3:
        grouped = "." + int_part[-3:] + grouped
        int_part = int_part[:-3]
    return f"{sign}{int_part}{grouped},{dec_part}"
