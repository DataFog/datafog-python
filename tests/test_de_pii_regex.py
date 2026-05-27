import pytest

import datafog
from datafog.core import get_supported_entities
from datafog.engine import scan, scan_and_redact
from datafog.processing.text_processing.regex_annotator import RegexAnnotator
from datafog.services.text_service import TextService


@pytest.mark.parametrize(
    "label,text,expected",
    [
        ("DE_VAT_ID", "USt-IdNr DE 123456789 ist gesetzt.", "DE 123456789"),
        ("DE_VAT_ID", "USt-IdNr DE-123456789 liegt vor.", "DE-123456789"),
        (
            "DE_IBAN",
            "IBAN DE44500105175407324931 ist gueltig.",
            "DE44500105175407324931",
        ),
        (
            "DE_IBAN",
            "IBAN DE44 5001 0517 5407 3249 31 ist gueltig.",
            "DE44 5001 0517 5407 3249 31",
        ),
    ],
)
def test_german_regex_cases_require_german_locale_or_explicit_entity_type(
    label: str, text: str, expected: str
) -> None:
    default_result = RegexAnnotator().annotate(text)
    assert expected not in default_result[label]

    german_result = RegexAnnotator(locales=["de"]).annotate(text)
    assert expected in german_result[label]

    explicit_result = RegexAnnotator(enabled_labels=[label]).annotate(text)
    assert expected in explicit_result[label]


@pytest.mark.parametrize(
    "label,text,expected",
    [
        ("DE_TAX_ID", "Steuer-ID 12345678901 liegt vor.", "12345678901"),
        ("DE_TAX_ID", "Steuer-ID 12 345 678 901 ist gesetzt.", "12 345 678 901"),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65150804A123 liegt vor.",
            "65150804A123",
        ),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65 150804 A123 liegt vor.",
            "65 150804 A123",
        ),
        ("DE_POSTAL_CODE", "PLZ10115 Berlin.", "PLZ10115"),
        ("DE_POSTAL_CODE", "DE-10115 Berlin.", "DE-10115"),
        ("DE_PASSPORT_NUMBER", "Passnummer C12345678 wurde geprueft.", "C12345678"),
        (
            "DE_RESIDENCE_PERMIT_NUMBER",
            "Aufenthaltstitel AT1234567 gueltig.",
            "AT1234567",
        ),
    ],
)
def test_broad_german_regex_cases_require_german_locale(
    label: str, text: str, expected: str
) -> None:
    default_result = RegexAnnotator().annotate(text)
    assert expected not in default_result[label]

    german_result = RegexAnnotator(locales=["de"]).annotate(text)
    assert expected in german_result[label]


@pytest.mark.parametrize(
    "label,text",
    [
        ("DE_VAT_ID", "USt-IdNr DE12345678 liegt vor."),
        ("DE_VAT_ID", "USt-IdNr DE1234567890 liegt vor."),
        ("DE_VAT_ID", "USt-IdNr DE123456789A should not prefix-match."),
        ("DE_IBAN", "IBAN DE4450010517540732493 ist gueltig."),
        ("DE_IBAN", "IBAN DE44 5001 0517 5407 3249 3X ist gueltig."),
        ("DE_TAX_ID", "Invoice 12345678901 was paid."),
        ("DE_SOCIAL_SECURITY_NUMBER", "Build 65150804A123 failed."),
        ("DE_POSTAL_CODE", "SKU D12345 is not a postcode."),
        ("DE_POSTAL_CODE", "Release DE12345 shipped."),
        ("DE_PASSPORT_NUMBER", "Ticket A12345678 was shipped."),
        ("DE_RESIDENCE_PERMIT_NUMBER", "Order AT1234567 is internal."),
    ],
)
def test_german_regex_false_positive_guards(label: str, text: str) -> None:
    result = RegexAnnotator(locales=["de"]).annotate(text)
    assert not result[label]


def test_scan_locale_and_explicit_entity_type_activation() -> None:
    text = "Steuer-ID 12345678901 liegt vor."

    default_result = scan(text, engine="regex")
    assert "DE_TAX_ID" not in {entity.type for entity in default_result.entities}

    locale_result = scan(text, engine="regex", locales=["de"])
    assert [
        entity.text for entity in locale_result.entities if entity.type == "DE_TAX_ID"
    ] == ["12345678901"]

    explicit_result = scan(text, engine="regex", entity_types=["DE_TAX_ID"])
    assert [(entity.type, entity.text) for entity in explicit_result.entities] == [
        ("DE_TAX_ID", "12345678901")
    ]


def test_redaction_and_service_locale_support() -> None:
    text = "Passnummer C12345678 wurde geprueft."

    default_redaction = scan_and_redact(text, engine="regex")
    assert default_redaction.redacted_text == text

    locale_redaction = scan_and_redact(text, engine="regex", locales=["de"])
    assert "[DE_PASSPORT_NUMBER_1]" in locale_redaction.redacted_text

    service_result = TextService(locales=["de"]).annotate_text_sync(text)
    assert service_result["DE_PASSPORT_NUMBER"] == ["C12345678"]


@pytest.mark.parametrize(
    "text,vat_text",
    [
        ("USt-IdNr DE123456789 ist gesetzt.", "DE123456789"),
        ("USt-IdNr DE 123456789 ist gesetzt.", "DE 123456789"),
        ("USt-IdNr DE-123456789 ist gesetzt.", "DE-123456789"),
    ],
)
def test_german_vat_redaction_suppresses_inner_generic_ssn_match(
    text: str, vat_text: str
) -> None:
    scan_result = scan(text, engine="regex")
    assert scan_result.entities == []

    locale_scan_result = scan(text, engine="regex", locales=["de"])
    assert [(entity.type, entity.text) for entity in locale_scan_result.entities] == [
        ("DE_VAT_ID", vat_text)
    ]

    default_redaction = scan_and_redact(text, engine="regex")
    assert default_redaction.redacted_text == text

    redaction = scan_and_redact(text, engine="regex", locales=["de"])
    assert redaction.redacted_text == text.replace(vat_text, "[DE_VAT_ID_1]")


def test_top_level_helpers_and_supported_entities_respect_locale() -> None:
    default_entities = get_supported_entities()
    assert all(not entity.startswith("DE_") for entity in default_entities)

    german_entities = get_supported_entities(locales=["de"])
    assert "DE_VAT_ID" in german_entities
    assert "DE_IBAN" in german_entities
    assert "DE_TAX_ID" in german_entities
    assert "DE_RESIDENCE_PERMIT_NUMBER" in german_entities

    result = datafog.scan("Aufenthaltstitel AT1234567 gueltig.", locales=["de"])
    assert [(entity.type, entity.text) for entity in result.entities] == [
        ("DE_RESIDENCE_PERMIT_NUMBER", "AT1234567")
    ]
