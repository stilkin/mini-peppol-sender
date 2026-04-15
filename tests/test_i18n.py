"""Tests for peppol_sender.i18n — translation lookups, fallbacks, formatter."""

from decimal import Decimal

import pytest

from peppol_sender import i18n
from peppol_sender.i18n import _TRANSLATIONS, _UNIT_NAMES

_SUPPORTED_LANGS = ("en", "nl", "fr", "de")


# ---------- t() happy path ----------


@pytest.mark.parametrize("lang", _SUPPORTED_LANGS)
def test_t_returns_non_empty_string_for_every_key_and_language(lang: str) -> None:
    for key in _TRANSLATIONS["en"]:
        value = i18n.t(lang, key)
        assert isinstance(value, str)
        assert value, f"empty translation for {lang!r} / {key!r}"


def test_t_distinct_values_for_distinct_languages() -> None:
    # Sanity check that we're not accidentally returning EN everywhere.
    assert i18n.t("nl", "invoice") == "Factuur"
    assert i18n.t("fr", "invoice") == "Facture"
    assert i18n.t("de", "invoice") == "Rechnung"
    assert i18n.t("en", "invoice") == "Invoice"


def test_t_case_insensitive_language_code() -> None:
    assert i18n.t("NL", "invoice") == "Factuur"
    assert i18n.t("Fr", "invoice") == "Facture"


# ---------- t() fallbacks ----------


def test_t_unknown_language_falls_back_to_english() -> None:
    assert i18n.t("zz", "invoice") == "Invoice"


def test_t_unknown_key_returns_key_name() -> None:
    assert i18n.t("en", "no_such_key") == "no_such_key"


def test_t_unknown_language_and_unknown_key_returns_key() -> None:
    assert i18n.t("zz", "no_such_key") == "no_such_key"


# ---------- Structural invariant: all languages have the same key set ----------


@pytest.mark.parametrize("lang", [lang for lang in _SUPPORTED_LANGS if lang != "en"])
def test_translations_have_same_keys_as_english(lang: str) -> None:
    assert set(_TRANSLATIONS[lang].keys()) == set(_TRANSLATIONS["en"].keys()), (
        f"{lang!r} label dict has drifted from EN — add or remove keys to keep them in sync"
    )


@pytest.mark.parametrize("lang", [lang for lang in _SUPPORTED_LANGS if lang != "en"])
def test_unit_names_have_same_codes_as_english(lang: str) -> None:
    assert set(_UNIT_NAMES[lang].keys()) == set(_UNIT_NAMES["en"].keys()), (
        f"{lang!r} unit dict has drifted from EN — add or remove codes to keep them in sync"
    )


# ---------- unit_label() ----------


@pytest.mark.parametrize("lang", _SUPPORTED_LANGS)
def test_unit_label_resolves_every_code(lang: str) -> None:
    for code in _UNIT_NAMES["en"]:
        value = i18n.unit_label(lang, code)
        assert isinstance(value, str)
        assert value


def test_unit_label_known_translations() -> None:
    assert i18n.unit_label("nl", "HUR") == "uur"
    assert i18n.unit_label("fr", "HUR") == "heure"
    assert i18n.unit_label("de", "HUR") == "Stunde"
    assert i18n.unit_label("en", "HUR") == "hour"


def test_unit_label_unknown_language_falls_back_to_english() -> None:
    assert i18n.unit_label("zz", "HUR") == "hour"


def test_unit_label_unknown_code_returns_raw_code() -> None:
    assert i18n.unit_label("en", "XYZ") == "XYZ"
    assert i18n.unit_label("nl", "XYZ") == "XYZ"


# ---------- all_labels() ----------


def test_all_labels_returns_complete_dict() -> None:
    labels = i18n.all_labels("nl")
    assert set(labels.keys()) == set(_TRANSLATIONS["en"].keys())
    assert labels["invoice"] == "Factuur"
    assert labels["subtotal"] == "Subtotaal"


def test_all_labels_fills_english_for_unknown_language() -> None:
    labels = i18n.all_labels("zz")
    assert labels["invoice"] == "Invoice"
    assert labels["subtotal"] == "Subtotal"


# ---------- format_amount() ----------


@pytest.mark.parametrize(
    "value, expected",
    [
        (Decimal("0"), "0,00"),
        (Decimal("0.5"), "0,50"),
        (Decimal("1"), "1,00"),
        (Decimal("99.99"), "99,99"),
        (Decimal("999.99"), "999,99"),
        (Decimal("1000"), "1.000,00"),
        (Decimal("1234.56"), "1.234,56"),
        (Decimal("12345.67"), "12.345,67"),
        (Decimal("1000000"), "1.000.000,00"),
        (Decimal("1234567.89"), "1.234.567,89"),
        (Decimal("-1234.56"), "-1.234,56"),
        (Decimal("-0.01"), "-0,01"),
    ],
)
def test_format_amount(value: Decimal, expected: str) -> None:
    assert i18n.format_amount(value) == expected


def test_format_amount_rounds_half_to_even() -> None:
    # Python's Decimal quantize default is ROUND_HALF_EVEN — 999.995 rounds to 1000.00
    # because "0" is the nearest even digit. This matches the _dec() helpers used
    # elsewhere in the codebase (pdf.py, ubl.py).
    assert i18n.format_amount(Decimal("999.995")) == "1.000,00"
    # 999.985 rounds DOWN to 999.98 because "8" is even.
    assert i18n.format_amount(Decimal("999.985")) == "999,98"


def test_format_amount_one_decimal() -> None:
    # Values with fewer than 2 decimals get padded.
    assert i18n.format_amount(Decimal("99.9")) == "99,90"
