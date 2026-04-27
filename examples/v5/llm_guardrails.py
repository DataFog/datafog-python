"""OpenAI-style prompt and output protection with DataFog v5.

This example deliberately avoids importing an LLM SDK. Pass any client object
that exposes ``client.chat.completions.create(...)``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import datafog

from .utils import content_from_chat_response


MODEL = "gpt-4.1-mini"
SYSTEM_PROMPT = "You are a concise support assistant."


def protect_prompt(prompt: str) -> str:
    """Redact prompt text before it leaves the process."""
    return datafog.sanitize(prompt, engine="regex", policy="llm")


def filter_model_output(output: str) -> str:
    """Redact model text before returning it to a user or log sink."""
    return datafog.filter_output(output, engine="regex", policy="llm").redacted_text


def filter_streaming_output(chunks: Iterable[str]) -> list[str]:
    """Filter streaming model chunks, including entities split across chunks."""
    return list(datafog.filter_stream(chunks, engine="regex", policy="llm"))


def call_openai_style_chat(client: Any, user_prompt: str) -> str:
    """Call an OpenAI-style chat client with prompt and output protection."""
    safe_prompt = protect_prompt(user_prompt)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": safe_prompt},
        ],
    )
    return filter_model_output(content_from_chat_response(response))


if __name__ == "__main__":
    prompt = "Summarize this customer note: jane@example.com needs help."
    print(protect_prompt(prompt))
