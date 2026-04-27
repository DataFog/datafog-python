"""Tests for v5 policy models and enforcement."""

from __future__ import annotations

import pytest

import datafog
from datafog.engine import Entity, redact, scan
from datafog.exceptions import PolicyViolationError
from datafog.models import EntityPolicy, RedactionPolicy, TokenSession


def test_redaction_policy_canonicalizes_entity_types() -> None:
    policy = RedactionPolicy(entity_types={"email", "phone_number"})

    assert policy.entity_types == frozenset({"EMAIL", "PHONE"})


def test_builtin_llm_policy_denies_raw_text_even_when_requested() -> None:
    result = scan(
        "Email jane@example.com",
        engine="regex",
        include_text=True,
        policy="llm",
    )

    assert result.policy_name == "llm"
    assert result.include_text is False
    assert result.entities[0].text is None


def test_global_raw_text_disable_overrides_per_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAFOG_DISABLE_RAW_TEXT", "1")

    result = scan(
        "Email jane@example.com",
        engine="regex",
        include_text=True,
    )

    assert result.include_text is False
    assert result.entities[0].text is None


def test_policy_filters_entities_by_type_and_threshold() -> None:
    policy = RedactionPolicy(
        entity_types={"EMAIL"},
        threshold=0.9,
    )

    result = scan(
        "Email jane@example.com and SSN 123-45-6789",
        engine="regex",
        policy=policy,
    )

    assert {entity.type for entity in result.entities} == {"EMAIL"}


def test_redact_policy_default_action_masks() -> None:
    result = datafog.redact(
        "Email jane@example.com",
        policy=RedactionPolicy(name="mask-test", default_action="mask"),
    )

    assert result.policy_name == "mask-test"
    assert result.redacted_text == "Email ****************"
    assert result.replacements[0].action == "mask"


def test_redact_policy_per_entity_action_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAFOG_HMAC_KEY", "test-key")
    policy = RedactionPolicy(
        name="mixed",
        default_action="mask",
        entities={"EMAIL": EntityPolicy(action="hmac")},
    )

    result = datafog.redact("Email jane@example.com", policy=policy)

    assert result.replacements[0].action == "hmac"
    assert result.redacted_text.startswith("Email [EMAIL_")
    assert "jane@example.com" not in result.redacted_text


def test_redact_strict_policy_blocks() -> None:
    with pytest.raises(PolicyViolationError, match="blocked EMAIL"):
        datafog.redact("Email jane@example.com", policy="strict")


def test_redact_drop_and_warn_actions_do_not_store_raw_value() -> None:
    text = "Email jane@example.com and phone 415-555-1212"
    policy = RedactionPolicy(
        default_action="drop",
        entities={"PHONE": EntityPolicy(action="warn")},
    )

    result = datafog.redact(text, policy=policy)

    assert result.redacted_text == "Email  and phone 415-555-1212"
    assert result.replacements[0].action == "drop"
    assert result.replacements[0].replacement == ""
    assert result.replacements[1].action == "warn"
    assert result.replacements[1].replacement is None
    assert "jane@example.com" not in result.to_safe_json()


def test_policy_mapping_mode_session_requires_explicit_session() -> None:
    policy = RedactionPolicy(mapping_mode="session")
    entities = [
        Entity(
            type="EMAIL",
            start=6,
            end=22,
            confidence=1.0,
            severity="high",
            detector="regex.email",
        )
    ]

    with pytest.raises(ValueError, match="requires an explicit TokenSession"):
        redact("Email jane@example.com", entities=entities, policy=policy)


def test_policy_mapping_mode_session_uses_provided_session() -> None:
    session = TokenSession()
    policy = RedactionPolicy(mapping_mode="session")

    result = datafog.redact(
        "Email jane@example.com",
        policy=policy,
        session=session,
    )

    assert result.redacted_text == "Email [DF_EMAIL_1]"
    assert (
        datafog.restore(result.redacted_text, session=session)
        == "Email jane@example.com"
    )
