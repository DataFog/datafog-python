"""Shared helpers for v5 workflow examples."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import datafog


def redact_text(text: str, *, guardrail: datafog.Guardrail | None = None) -> str:
    """Redact a single text value with the v5 LLM-safe defaults."""
    active_guardrail = guardrail or datafog.create_guardrail(
        engine="regex",
        policy="llm",
    )
    return active_guardrail.filter(text).redacted_text


def redact_nested(value: Any, *, guardrail: datafog.Guardrail | None = None) -> Any:
    """Return a copy of a JSON-like value with string leaves redacted."""
    active_guardrail = guardrail or datafog.create_guardrail(
        engine="regex",
        policy="llm",
    )

    if isinstance(value, str):
        return redact_text(value, guardrail=active_guardrail)
    if isinstance(value, Mapping):
        return {
            key: redact_nested(item, guardrail=active_guardrail)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_nested(item, guardrail=active_guardrail) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact_nested(item, guardrail=active_guardrail) for item in value]
    return value


def content_from_chat_response(response: Any) -> str:
    """Extract assistant text from common OpenAI-style chat response shapes."""
    if isinstance(response, Mapping):
        choices = response.get("choices") or []
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

    if isinstance(response, str):
        return response
    return str(response)
