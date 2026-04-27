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

    assert any(entity.type == "EMAIL" for entity in result.entities)
    assert all(entity.text is None for entity in result.entities)
    assert result.input_length == len(prompt)
    assert prompt == "Customer email: jane.doe@company.com"


def test_filter_output_returns_safe_redact_result() -> None:
    output = "SSN: 123-45-6789"
    result = datafog.filter_output(output, engine="regex")

    assert result.redacted_text != output
    assert result.entities
    assert result.replacements[0].token.startswith("[SSN_")
    assert "123-45-6789" not in result.to_safe_json()


def test_filter_stream_redacts_entity_across_chunk_boundaries() -> None:
    chunks = ["Contact adm", "in@example", ".com for help"]

    filtered = list(datafog.filter_stream(chunks, engine="regex"))

    assert filtered == ["Contact [EMAIL_1] for help"]


def test_guardrail_filter_stream_block_mode_raises_after_buffering() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="block")
    chunks = ["Contact blocked", "@example.com"]

    with pytest.raises(GuardrailBlockedError, match="Guardrail blocked"):
        list(guard.filter_stream(chunks))


def test_guardrail_filter_stream_warn_mode_returns_original() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="warn")
    chunks = ["Contact warn", "@example.com"]

    with pytest.warns(UserWarning, match="Guardrail detected"):
        filtered = list(guard.filter_stream(chunks))

    assert filtered == ["Contact warn@example.com"]


def test_filter_stream_rejects_non_string_chunks() -> None:
    chunks = ["ok", b"not text"]

    with pytest.raises(TypeError, match="stream chunks must be strings"):
        list(datafog.filter_stream(chunks, engine="regex"))  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_filter_async_stream_redacts_entity_across_chunk_boundaries() -> None:
    async def chunks():
        for chunk in ["Contact as", "ync@example", ".com"]:
            yield chunk

    filtered = [
        chunk async for chunk in datafog.filter_async_stream(chunks(), engine="regex")
    ]

    assert filtered == ["Contact [EMAIL_1]"]


@pytest.mark.asyncio
async def test_guardrail_filter_async_stream_block_mode_raises() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="block")

    async def chunks():
        for chunk in ["Contact async-blocked", "@example.com"]:
            yield chunk

    with pytest.raises(GuardrailBlockedError, match="Guardrail blocked"):
        [chunk async for chunk in guard.filter_async_stream(chunks())]


@pytest.mark.asyncio
async def test_guardrail_filter_async_stream_warn_mode_returns_original() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="warn")

    async def chunks():
        for chunk in ["Contact async-warn", "@example.com"]:
            yield chunk

    with pytest.warns(UserWarning, match="Guardrail detected"):
        filtered = [chunk async for chunk in guard.filter_async_stream(chunks())]

    assert filtered == ["Contact async-warn@example.com"]


def test_create_guardrail_as_decorator_redacts_string_output() -> None:
    guard = datafog.create_guardrail(engine="regex", on_detect="redact")

    @guard
    def fake_llm() -> str:
        return "Contact: admin@example.com"

    filtered = fake_llm()
    assert "[EMAIL_1]" in filtered
    assert "admin@example.com" not in filtered


def test_protect_decorator_redacts_sync_string_output() -> None:
    @datafog.protect(engine="regex", on_detect="redact")
    def fake_llm() -> str:
        return "Contact: admin@example.com"

    filtered = fake_llm()

    assert "[EMAIL_1]" in filtered
    assert "admin@example.com" not in filtered


@pytest.mark.asyncio
async def test_protect_decorator_redacts_async_string_output() -> None:
    @datafog.protect(engine="regex", on_detect="redact")
    async def fake_llm() -> str:
        return "Contact: async@example.com"

    filtered = await fake_llm()

    assert "[EMAIL_1]" in filtered
    assert "async@example.com" not in filtered


@pytest.mark.asyncio
async def test_protect_decorator_async_block_mode_raises() -> None:
    @datafog.protect(engine="regex", on_detect="block")
    async def fake_llm() -> str:
        return "Contact: async-blocked@example.com"

    with pytest.raises(GuardrailBlockedError, match="Guardrail blocked"):
        await fake_llm()


@pytest.mark.asyncio
async def test_protect_decorator_async_warn_mode_warns() -> None:
    text = "Contact: async-warn@example.com"

    @datafog.protect(engine="regex", on_detect="warn")
    async def fake_llm() -> str:
        return text

    with pytest.warns(UserWarning, match="Guardrail detected"):
        filtered = await fake_llm()

    assert filtered == text


def test_protect_decorator_block_mode_raises() -> None:
    @datafog.protect(engine="regex", on_detect="block")
    def fake_llm() -> str:
        return "Contact: blocked@example.com"

    with pytest.raises(GuardrailBlockedError, match="Guardrail blocked"):
        fake_llm()


def test_protect_decorator_warn_mode_warns_and_returns_original() -> None:
    text = "Contact: warn-decorator@example.com"

    @datafog.protect(engine="regex", on_detect="warn")
    def fake_llm() -> str:
        return text

    with pytest.warns(UserWarning, match="Guardrail detected"):
        filtered = fake_llm()

    assert filtered == text


def test_protect_decorator_leaves_non_string_output_unchanged() -> None:
    payload = {"message": "Contact admin@example.com"}

    @datafog.protect(engine="regex", on_detect="redact")
    def fake_tool() -> dict[str, str]:
        return payload

    assert fake_tool() is payload


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
    assert result.replacements == []


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
