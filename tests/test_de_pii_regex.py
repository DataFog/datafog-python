import pytest

from datafog.processing.text_processing.regex_annotator import RegexAnnotator


@pytest.mark.parametrize(
    "label,text,expected",
    [
        (
            "DE_TAX_ID",
            "Steuer-ID 12345678901 liegt vor.",
            "12345678901",
        ),
        (
            "DE_TAX_ID",
            "Steuer-ID 12 345 678 901 ist gesetzt.",
            "12 345 678 901",
        ),
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
        (
            "DE_POSTAL_CODE",
            "PLZ10115 Berlin.",
            "PLZ10115",
        ),
        (
            "DE_POSTAL_CODE",
            "DE10115 Berlin.",
            "DE10115",
        ),
        (
            "DE_PASSPORT_NUMBER",
            "Passnummer C12345678 wurde geprueft.",
            "C12345678",
        ),
        (
            "DE_RESIDENCE_PERMIT_NUMBER",
            "Aufenthaltstitel AT1234567 gueltig.",
            "AT1234567",
        ),
    ],
)
def test_de_regex_positive_cases(label: str, text: str, expected: str) -> None:
    annotator = RegexAnnotator()
    result = annotator.annotate(text)
    assert expected in result[label]


@pytest.mark.parametrize(
    "label,text",
    [
        ("DE_TAX_ID", "Steuer-ID 1234567890 liegt vor."),
        ("DE_TAX_ID", "Steuer-ID 123456789012 liegt vor."),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65150804123 liegt vor.",
        ),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65150804AA23 liegt vor.",
        ),
        ("DE_POSTAL_CODE", "10115 Berlin."),
        ("DE_PASSPORT_NUMBER", "Passnummer 12345678 wurde geprueft."),
        (
            "DE_RESIDENCE_PERMIT_NUMBER",
            "Aufenthaltstitel AT12345678 gueltig.",
        ),
    ],
)
def test_de_regex_negative_cases(label: str, text: str) -> None:
    annotator = RegexAnnotator()
    result = annotator.annotate(text)
    assert not result[label]
