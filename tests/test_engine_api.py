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


def test_gliner_engine_unavailable_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
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
