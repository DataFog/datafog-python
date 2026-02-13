"""Tests for the agent-oriented API surface."""

from __future__ import annotations

import pytest

import datafog
from datafog.agent import GuardrailBlockedError


def test_sanitize_redacts_structured_pii() -> None:
    text = "Reach me at john@example.com or (555) 123-4567."
    redacted = datafog.sanitize(text, engine="regex")

    assert redacted != text
    assert "[EMAIL_1]" in redacted
    assert "[PHONE_1]" in redacted


def test_scan_prompt_returns_entities_without_modifying_text() -> None:
    prompt = "Customer email: jane.doe@company.com"
    result = datafog.scan_prompt(prompt, engine="regex")

    assert result.text == prompt
    assert any(entity.type == "EMAIL" for entity in result.entities)
    assert prompt == "Customer email: jane.doe@company.com"


def test_filter_output_returns_redact_result_and_mapping() -> None:
    output = "SSN: 123-45-6789"
    result = datafog.filter_output(output, engine="regex")

    assert result.redacted_text != output
    assert result.entities
    assert any(key.startswith("[SSN_") for key in result.mapping)
    assert "123-45-6789" in result.mapping.values()


def test_create_guardrail_as_decorator_redacts_string_output() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="redact")

    @guard
    def fake_llm() -> str:
        return "Contact: admin@example.com"

    filtered = fake_llm()
    assert "[EMAIL_1]" in filtered
    assert "admin@example.com" not in filtered


def test_create_guardrail_block_mode_raises() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="block")

    with pytest.raises(GuardrailBlockedError):
        guard.filter("Email me at blocked@example.com")


def test_create_guardrail_warn_mode_warns_and_returns_original() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="warn")
    text = "Send to warn@example.com"

    with pytest.warns(UserWarning, match="Guardrail detected"):
        result = guard.filter(text)

    assert result.redacted_text == text
    assert result.entities
    assert result.mapping == {}


def test_guardrail_watch_context_manager_tracks_activity() -> None:
    guard = datafog.create_guardrail(engine="regex")

    with guard.watch() as watcher:
        scan_result = watcher.scan("Email: watch@example.com")
        filter_result = watcher.filter("SSN 123-45-6789")

    assert scan_result.entities
    assert filter_result.redacted_text != "SSN 123-45-6789"
    assert watcher.detections >= 2
    assert watcher.redactions == 1


def test_agent_api_edge_cases_empty_and_no_pii() -> None:
    assert datafog.sanitize("", engine="regex") == ""
    assert datafog.scan_prompt("", engine="regex").entities == []

    clean = "No personal data here."
    result = datafog.filter_output(clean, engine="regex")
    assert result.redacted_text == clean
    assert result.entities == []


def test_sanitize_all_structured_types_in_one_text() -> None:
    text = (
        "Email a@b.co, phone (555) 123-4567, ssn 123-45-6789, card 4111-1111-1111-1111, "
        "ip 10.0.0.1, date 2024-01-31, zip 94107."
    )
    redacted = datafog.sanitize(text, engine="regex")

    assert "[EMAIL_1]" in redacted
    assert "[PHONE_1]" in redacted
    assert "[SSN_1]" in redacted
    assert "[CREDIT_CARD_1]" in redacted
    assert "[IP_ADDRESS_1]" in redacted
    assert "[DATE_1]" in redacted
    assert "[ZIP_CODE_1]" in redacted
