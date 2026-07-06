"""Tests for the internal engine boundary API."""

from __future__ import annotations

import pytest

from datafog.engine import Entity, redact, scan, scan_and_redact
from datafog.exceptions import EngineNotAvailable


def test_scan_regex_detects_structured_entities() -> None:
    result = scan("Email john@example.com and SSN 123-45-6789", engine="regex")

    entity_types = {entity.type for entity in result.entities}
    assert "EMAIL" in entity_types
    assert "SSN" in entity_types
    assert result.engine_used == "regex"


def test_scan_filters_entity_types() -> None:
    result = scan(
        "Email john@example.com and SSN 123-45-6789",
        engine="regex",
        entity_types=["EMAIL"],
    )
    assert result.entities
    assert {entity.type for entity in result.entities} == {"EMAIL"}


def test_scan_invalid_engine_raises_value_error() -> None:
    with pytest.raises(ValueError, match="engine must be one of"):
        scan("test", engine="invalid")


def test_scan_non_string_raises_type_error() -> None:
    with pytest.raises(TypeError, match="text must be a string"):
        scan(None, engine="regex")  # type: ignore[arg-type]


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_redact_strategies(strategy: str) -> None:
    text = "Contact john@example.com"
    entities = [
        Entity(
            type="EMAIL",
            text="john@example.com",
            start=8,
            end=24,
            confidence=1.0,
            engine="regex",
        )
    ]

    result = redact(text=text, entities=entities, strategy=strategy)
    assert result.redacted_text != text
    assert result.mapping


def _entity_at(text: str, value: str, entity_type: str = "EMAIL") -> Entity:
    start = text.index(value)
    return Entity(
        type=entity_type,
        text=value,
        start=start,
        end=start + len(value),
        confidence=1.0,
        engine="regex",
    )


def test_redact_token_numbering_follows_document_order() -> None:
    text = "first alpha@example.com then beta@example.com end"
    entities = [
        _entity_at(text, "alpha@example.com"),
        _entity_at(text, "beta@example.com"),
    ]

    result = redact(text=text, entities=entities, strategy="token")

    assert result.redacted_text == "first [EMAIL_1] then [EMAIL_2] end"
    assert result.mapping == {
        "[EMAIL_1]": "alpha@example.com",
        "[EMAIL_2]": "beta@example.com",
    }


def test_redact_pseudonymize_numbering_follows_document_order() -> None:
    text = "first alpha@example.com then beta@example.com end"
    entities = [
        _entity_at(text, "alpha@example.com"),
        _entity_at(text, "beta@example.com"),
    ]

    result = redact(text=text, entities=entities, strategy="pseudonymize")

    assert result.redacted_text == "first [EMAIL_PSEUDO_1] then [EMAIL_PSEUDO_2] end"
    assert result.mapping == {
        "[EMAIL_PSEUDO_1]": "alpha@example.com",
        "[EMAIL_PSEUDO_2]": "beta@example.com",
    }


def _span(
    text: str,
    start: int,
    end: int,
    entity_type: str = "PHONE",
    confidence: float = 1.0,
    engine: str = "regex",
) -> Entity:
    return Entity(
        type=entity_type,
        text=text[start:end],
        start=start,
        end=end,
        confidence=confidence,
        engine=engine,
    )


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_redact_overlapping_spans_match_longest_only(strategy: str) -> None:
    text = "call 555-000-1111 now"
    full = _span(text, 5, 17)
    suffix = _span(text, 9, 17)

    result = redact(text=text, entities=[full, suffix], strategy=strategy)
    expected = redact(text=text, entities=[full], strategy=strategy)

    assert result.redacted_text == expected.redacted_text
    assert result.mapping == expected.mapping
    assert result.entities == [full]


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_redact_nested_spans_keep_outer(strategy: str) -> None:
    text = "mail alice@example.com today"
    outer = _span(text, 5, 22, entity_type="EMAIL")
    inner = _span(text, 11, 18, entity_type="EMAIL")

    result = redact(text=text, entities=[inner, outer], strategy=strategy)
    expected = redact(text=text, entities=[outer], strategy=strategy)

    assert result.redacted_text == expected.redacted_text
    assert result.mapping == expected.mapping
    assert result.entities == [outer]


def test_redact_overlapping_spans_produce_clean_token_output() -> None:
    text = "call 555-000-1111 now"
    entities = [_span(text, 5, 17), _span(text, 9, 17)]

    result = redact(text=text, entities=entities, strategy="token")

    assert result.redacted_text == "call [PHONE_1] now"
    assert result.mapping == {"[PHONE_1]": text[5:17]}


def test_redact_duplicate_spans_applied_once() -> None:
    text = "mail alice@example.com today"
    entity = _entity_at(text, "alice@example.com")

    result = redact(text=text, entities=[entity, entity], strategy="token")

    assert result.redacted_text == "mail [EMAIL_1] today"
    assert result.entities == [entity]


def test_redact_overlap_tiebreak_prefers_higher_confidence() -> None:
    text = "Acme Corporation announced"
    org = _span(text, 0, 16, entity_type="ORGANIZATION", confidence=0.7, engine="spacy")
    person = _span(text, 0, 16, entity_type="PERSON", confidence=0.9, engine="gliner")

    result = redact(text=text, entities=[org, person], strategy="token")

    assert result.redacted_text == "[PERSON_1] announced"
    assert result.entities == [person]


def test_redact_mask_mapping_distinguishes_same_length_values() -> None:
    text = "a alice@example.com b bobby@example.com c"
    entities = [
        _entity_at(text, "alice@example.com"),
        _entity_at(text, "bobby@example.com"),
    ]

    result = redact(text=text, entities=entities, strategy="mask")

    assert result.redacted_text == "a " + "*" * 17 + " b " + "*" * 17 + " c"
    assert result.mapping == {
        "[EMAIL_MASK_1]": "alice@example.com",
        "[EMAIL_MASK_2]": "bobby@example.com",
    }


def test_redact_invalid_strategy_raises_value_error() -> None:
    with pytest.raises(ValueError, match="strategy must be one of"):
        redact("test", entities=[], strategy="invalid")


def test_redact_ignores_invalid_spans() -> None:
    text = "hello"
    entities = [
        Entity(
            type="EMAIL",
            text="x",
            start=-1,
            end=2,
            confidence=1.0,
            engine="regex",
        ),
        Entity(
            type="EMAIL",
            text="x",
            start=2,
            end=10,
            confidence=1.0,
            engine="regex",
        ),
    ]

    result = redact(text=text, entities=entities, strategy="token")
    assert result.redacted_text == text
    assert result.mapping == {}


def test_scan_and_redact_combines_operations() -> None:
    text = "Call me at (555) 123-4567"
    result = scan_and_redact(text=text, engine="regex", strategy="token")

    assert result.entities
    assert "[PHONE_1]" in result.redacted_text


@pytest.mark.asyncio
async def test_scan_from_async_context() -> None:
    """Verify sync engine API works when called from async code."""
    result = scan("john@example.com", engine="regex")
    assert len(result.entities) >= 1


def test_gliner_engine_unavailable_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_: str):
        raise EngineNotAvailable(
            "GLiNER engine requires the nlp-advanced extra. Install with: pip install datafog[nlp-advanced]"
        )

    monkeypatch.setattr("datafog.engine._gliner_entities", _raise)

    with pytest.raises(EngineNotAvailable, match="nlp-advanced"):
        scan("john@example.com", engine="gliner")


def test_smart_engine_degrades_to_regex_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_: str):
        raise EngineNotAvailable("not installed")

    monkeypatch.setattr("datafog.engine._gliner_entities", _raise)
    monkeypatch.setattr("datafog.engine._spacy_entities", _raise)

    with pytest.warns(UserWarning, match="regex only"):
        result = scan("john@example.com", engine="smart")

    assert any(entity.type == "EMAIL" for entity in result.entities)
