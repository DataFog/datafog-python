import pytest

from datafog.processing.text_processing.regex_annotator import RegexAnnotator


VALID_DE_TAX_ID = "12345678903"
VALID_DE_TAX_ID_SPACED = "12 345 678 903"
INVALID_DE_TAX_ID = (
    VALID_DE_TAX_ID[:-1]
    + str((int(VALID_DE_TAX_ID[-1]) + 1) % 10)
)


@pytest.mark.parametrize(
    "label,text,expected",
    [
        (
            "DE_VAT_ID",
            "USt-IdNr DE 123456789 ist gesetzt.",
            "DE 123456789",
        ),
        (
            "DE_VAT_ID",
            "USt-IdNr DE-123456789 liegt vor.",
            "DE-123456789",
        ),
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
        (
            "DE_TAX_ID",
            f"Steuer-ID {VALID_DE_TAX_ID} liegt vor.",
            VALID_DE_TAX_ID,
        ),
        (
            "DE_TAX_ID",
            f"Steuer-ID {VALID_DE_TAX_ID_SPACED} ist gesetzt.",
            VALID_DE_TAX_ID_SPACED,
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
            "PLZ 10115 Berlin.",
            "PLZ 10115",
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
    annotator = RegexAnnotator(locales=["de"])
    result = annotator.annotate(text)
    assert expected in result[label]


@pytest.mark.parametrize(
    "label,text",
    [
        ("DE_VAT_ID", "USt-IdNr DE12345678 liegt vor."),
        ("DE_VAT_ID", "USt-IdNr DE1234567890 liegt vor."),
        ("DE_IBAN", "IBAN DE4450010517540732493 ist gueltig."),
        ("DE_IBAN", "IBAN DE44 5001 0517 5407 3249 3X ist gueltig."),
        ("DE_TAX_ID", "Steuer-ID 1234567890 liegt vor."),
        ("DE_TAX_ID", "Steuer-ID 123456789012 liegt vor."),
        ("DE_TAX_ID", f"Steuer-ID {INVALID_DE_TAX_ID} liegt vor."),
        ("DE_TAX_ID", "Steuer-ID 12345678901 liegt vor."),
        ("DE_TAX_ID", "Steuer-ID 01234567890 liegt vor."),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65150804123 liegt vor.",
        ),
        (
            "DE_SOCIAL_SECURITY_NUMBER",
            "Rentenversicherungsnummer 65150804AA23 liegt vor.",
        ),
        ("DE_POSTAL_CODE", "10115 Berlin."),
        ("DE_POSTAL_CODE", "D12345"),
        ("DE_POSTAL_CODE", "DE12345"),
        ("DE_POSTAL_CODE", "DE10115 Berlin."),
        ("DE_POSTAL_CODE", "D10115 Berlin."),
        ("DE_PASSPORT_NUMBER", "Passnummer 12345678 wurde geprueft."),
        ("DE_PASSPORT_NUMBER", "Bestellung A12345678 liegt vor."),
        (
            "DE_RESIDENCE_PERMIT_NUMBER",
            "Aufenthaltstitel AT12345678 gueltig.",
        ),
        (
            "DE_RESIDENCE_PERMIT_NUMBER",
            "AT1234567 ohne Kontext.",
        ),
    ],
)
def test_de_regex_negative_cases(label: str, text: str) -> None:
    annotator = RegexAnnotator(locales=["de"])
    result = annotator.annotate(text)
    assert not result[label]
