"""Core 1.5 candidate seam regressions; exercised before the dependency floor moves."""

import importlib.metadata

import pytest

import datafog

pytestmark = pytest.mark.skipif(
    importlib.metadata.version("datafog-core").split(".")[:2] != ["1", "5"],
    reason="qualifies the separately built Core 1.5 candidate before publication",
)


@pytest.mark.parametrize("value", ["::ffff:192.168.1.1", "64:ff9b::192.0.2.33"])
def test_ipv6_embedded_ipv4_tail_is_fully_redacted(value):
    result = datafog.redact(value)
    assert result.redacted_text == "[IP_ADDRESS_1]"
    assert result.mapping == {"[IP_ADDRESS_1]": value}


def test_contextual_email_does_not_swallow_neighboring_phone():
    text = "phone=415-555-2671&email=bob@example.com"
    result = datafog.scan(text)
    assert [(item.type, item.text) for item in result.entities] == [
        ("PHONE", "415-555-2671"),
        ("EMAIL", "bob@example.com"),
    ]
    assert datafog.redact(text).redacted_text == "phone=[PHONE_1]&email=[EMAIL_1]"


def test_phone_followed_by_zip_does_not_become_credit_card():
    text = "555-123-4567 94105"
    assert [(item.type, item.text) for item in datafog.scan(text).entities] == [
        ("PHONE", "555-123-4567"),
        ("ZIP_CODE", "94105"),
    ]
    assert datafog.scan(text, entity_types=["PHONE"]).entities[0].text == "555-123-4567"


def test_adding_model_selection_does_not_drop_large_document_ssns():
    text = "ssn 123-45-6789 " * 3000
    result = datafog.scan(text, entity_types=["SSN", "PERSON"])
    assert len([item for item in result.entities if item.type == "SSN"]) == 3000
    assert all(text[item.start : item.end] == item.text for item in result.entities)


def test_international_email_and_person_punctuation():
    assert datafog.scan("mail jörg@müller.de").entities[0].text == "jörg@müller.de"
    result = datafog.scan("Jane Doe,\n14 Penny Lane", entity_types=["PERSON"])
    assert result.entities and all(
        item.text == item.text.rstrip(",;:.!?") for item in result.entities
    )


def test_german_context_prevents_generic_false_positive_labels():
    assert not datafog.scan("Steuer-ID 12345678901 liegt vor.").entities
    assert not datafog.scan("IBAN DE44 5001 0517 5407 3249 31 ist gueltig.").entities
