"""Tests for the internal engine boundary API."""

from __future__ import annotations

import pytest

from datafog.engine import Entity, redact, restore, scan, scan_and_redact
from datafog.exceptions import EngineNotAvailable
from datafog.models import TokenSession


def test_scan_regex_detects_structured_entities() -> None:
    result = scan("Email john@example.com and SSN 123-45-6789", engine="regex")

    entity_types = {entity.type for entity in result.entities}
    assert "EMAIL" in entity_types
    assert "SSN" in entity_types
    assert result.input_length == len("Email john@example.com and SSN 123-45-6789")
    assert result.engine == "regex"
    assert result.engine_used == "regex"
    assert all(entity.text is None for entity in result.entities)


def test_scan_can_include_raw_text_explicitly() -> None:
    result = scan("Email john@example.com", engine="regex", include_text=True)

    assert any(entity.text == "john@example.com" for entity in result.entities)
    assert result.to_safe_dict()["entities"][0]["text"] is None


def test_scan_filters_entity_types() -> None:
    result = scan(
        "Email john@example.com and SSN 123-45-6789",
        engine="regex",
        entity_types=["EMAIL"],
    )
    assert result.entities
    assert {entity.type for entity in result.entities} == {"EMAIL"}


def test_scan_detects_p0_secret_patterns() -> None:
    result = scan(
        "token sk-proj-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa and uuid "
        "123e4567-e89b-12d3-a456-426614174000",
        engine="regex",
    )

    by_type = {entity.type: entity for entity in result.entities}
    assert by_type["OPENAI_API_KEY"].severity == "critical"
    assert by_type["UUID"].severity == "medium"
    assert by_type["OPENAI_API_KEY"].text is None


def test_scan_invalid_engine_raises_value_error() -> None:
    with pytest.raises(ValueError, match="engine must be one of"):
        scan("test", engine="invalid")


def test_scan_non_string_raises_type_error() -> None:
    with pytest.raises(TypeError, match="text must be a string"):
        scan(None, engine="regex")  # type: ignore[arg-type]


@pytest.mark.parametrize("strategy", ["token", "mask", "pseudonymize"])
def test_redact_strategies(strategy: str) -> None:
    text = "Contact john@example.com"
    entities = [
        Entity(
            type="EMAIL",
            start=8,
            end=24,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        )
    ]

    result = redact(text=text, entities=entities, strategy=strategy)
    assert result.redacted_text != text
    assert result.replacements
    assert all(entity.text is None for entity in result.entities)


@pytest.mark.parametrize("strategy", ["hmac", "hash", "hmac_sha256"])
def test_redact_hmac_strategies_require_key(strategy: str) -> None:
    with pytest.raises(ValueError, match="requires an HMAC key"):
        redact("Contact john@example.com", entities=[], strategy=strategy)


def test_redact_hash_alias_uses_hmac_key(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "Contact john@example.com"
    entities = [
        Entity(
            type="EMAIL",
            start=8,
            end=24,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        )
    ]
    monkeypatch.setenv("DATAFOG_HMAC_KEY", "test-key")

    result = redact(text=text, entities=entities, strategy="hash")

    assert result.redacted_text.startswith("Contact [EMAIL_")
    assert "john@example.com" not in result.redacted_text
    assert result.replacements[0].action == "hmac"


def test_token_session_reuses_value_tokens_and_restores() -> None:
    text = "Email sid@example.com, then sid@example.com again"
    entities = [
        Entity(
            type="EMAIL",
            start=6,
            end=21,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        ),
        Entity(
            type="EMAIL",
            start=28,
            end=43,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        ),
    ]
    session = TokenSession()

    result = redact(text=text, entities=entities, session=session)

    assert result.session_id == session.session_id
    assert result.redacted_text.count("[DF_EMAIL_1]") == 2
    assert session.mapping_count == 1
    assert restore(result.redacted_text, session=session) == text


def test_redact_invalid_strategy_raises_value_error() -> None:
    with pytest.raises(ValueError, match="strategy must be one of"):
        redact("test", entities=[], strategy="invalid")


def test_redact_ignores_invalid_spans() -> None:
    text = "hello"
    entities = [
        Entity(
            type="EMAIL",
            start=-1,
            end=2,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        ),
        Entity(
            type="EMAIL",
            start=2,
            end=10,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        ),
    ]

    result = redact(text=text, entities=entities, strategy="token")
    assert result.redacted_text == text
    assert result.replacements == []


def test_scan_and_redact_combines_operations() -> None:
    text = "Call me at (555) 123-4567"
    result = scan_and_redact(text=text, engine="regex", strategy="token")

    assert result.entities
    assert "[PHONE_1]" in result.redacted_text
    assert result.replacements[0].replacement == "[PHONE_1]"


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
