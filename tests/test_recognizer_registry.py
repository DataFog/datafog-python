"""Tests for custom recognizers and the v5 recognizer registry."""

from __future__ import annotations

import re

import pytest

import datafog
from datafog.models import RegexRecognizer, ValidationResult


@pytest.fixture(autouse=True)
def clear_custom_recognizers():
    datafog.clear_recognizers()
    yield
    datafog.clear_recognizers()


def test_per_call_regex_recognizer_detects_custom_entity() -> None:
    assert datafog.RegexRecognizer is RegexRecognizer
    recognizer = RegexRecognizer(
        entity_type="customer_id",
        pattern=r"CUST-\d{4}",
        confidence=0.92,
        description="Internal customer identifier",
    )

    result = datafog.scan(
        "Customer CUST-1234 opened a ticket",
        engine="regex",
        include_text=True,
        recognizers=[recognizer],
    )

    custom = [entity for entity in result.entities if entity.type == "CUSTOMER_ID"]
    assert len(custom) == 1
    assert custom[0].text == "CUST-1234"
    assert custom[0].confidence == 0.92
    assert custom[0].severity == "medium"
    assert custom[0].detector == "custom.customer_id"
    assert result.engine == "custom+regex"
    assert recognizer.to_dict() == {
        "name": "customer_id",
        "entity_type": "CUSTOMER_ID",
        "confidence": 0.92,
        "description": "Internal customer identifier",
        "detector": "custom.customer_id",
    }


def test_regex_recognizer_named_value_group_controls_span() -> None:
    recognizer = RegexRecognizer(
        entity_type="ticket_id",
        pattern=r"ticket=(?P<value>TCK-\d{3})",
    )

    result = datafog.scan(
        "metadata ticket=TCK-123 status=open",
        engine="regex",
        include_text=True,
        recognizers=[recognizer],
    )

    entity = next(entity for entity in result.entities if entity.type == "TICKET_ID")
    assert entity.text == "TCK-123"
    assert result.entities[0].start >= 0
    assert "ticket=" not in entity.text


def test_global_registry_applies_to_scan() -> None:
    registered = datafog.register_regex_recognizer(
        entity_type="workspace_id",
        pattern=r"ws_[a-z0-9]{6}",
        confidence=0.88,
        description="Workspace identifier",
    )

    result = datafog.scan("workspace ws_ab12cd", engine="regex", include_text=True)

    assert datafog.list_recognizers() == (registered,)
    assert any(
        entity.type == "WORKSPACE_ID" and entity.text == "ws_ab12cd"
        for entity in result.entities
    )


def test_recognizer_validator_filters_false_positives() -> None:
    def validator(value: str) -> bool:
        return value.endswith("42")

    recognizer = RegexRecognizer(
        entity_type="account_id",
        pattern=r"ACCT-\d{2}",
        validator=validator,
    )

    result = datafog.scan(
        "ignore ACCT-12 but keep ACCT-42",
        engine="regex",
        include_text=True,
        recognizers=[recognizer],
    )

    account_entities = [
        entity for entity in result.entities if entity.type == "ACCOUNT_ID"
    ]
    assert [entity.text for entity in account_entities] == ["ACCT-42"]
    assert account_entities[0].validation == ValidationResult(
        validator="account_id",
        status="valid",
    )


def test_recognizer_validator_can_attach_validation_result() -> None:
    def validator(_: str) -> ValidationResult:
        return ValidationResult(
            validator="ticket_checksum",
            status="valid",
            reason="checksum matched",
        )

    recognizer = RegexRecognizer(
        entity_type="ticket_id",
        pattern=r"TCK-\d{3}",
        validator=validator,
    )

    result = datafog.scan(
        "ticket TCK-123",
        engine="regex",
        recognizers=[recognizer],
    )

    entity = next(entity for entity in result.entities if entity.type == "TICKET_ID")
    assert entity.validation == ValidationResult(
        validator="ticket_checksum",
        status="valid",
        reason="checksum matched",
    )


def test_invalid_validation_result_skips_recognizer_match() -> None:
    recognizer = RegexRecognizer(
        entity_type="ticket_id",
        pattern=r"TCK-\d{3}",
        validator=lambda _: ValidationResult(
            validator="ticket_checksum",
            status="invalid",
        ),
    )

    result = datafog.scan(
        "ticket TCK-123",
        engine="regex",
        recognizers=[recognizer],
    )

    assert all(entity.type != "TICKET_ID" for entity in result.entities)


def test_custom_recognizer_detection_redacts() -> None:
    recognizer = RegexRecognizer(
        entity_type="customer_id",
        pattern=re.compile(r"CUST-\d{4}"),
    )

    result = datafog.redact(
        "Customer CUST-1234 opened a ticket",
        engine="regex",
        strategy="mask",
        recognizers=[recognizer],
    )

    assert result.redacted_text == "Customer ********* opened a ticket"
    assert result.entities[0].type == "CUSTOMER_ID"
    assert result.replacements[0].action == "mask"
