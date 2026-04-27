"""Smoke tests for v5 adoption examples."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from examples.v5 import (
    fastapi_request_filtering,
    langchain_adapter,
    llamaindex_adapter,
    llm_guardrails,
    logging_filter,
)


def test_llm_guardrails_redact_openai_style_prompt_and_output() -> None:
    class Completions:
        def __init__(self) -> None:
            self.messages: list[dict[str, str]] = []

        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
        ) -> dict[str, object]:
            self.messages = messages
            return {
                "choices": [
                    {"message": {"content": "Reply to jane@example.com"}},
                ],
            }

    completions = Completions()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )

    output = llm_guardrails.call_openai_style_chat(
        client,
        "Please help jane@example.com",
    )

    user_message = completions.messages[1]["content"]
    assert "jane@example.com" not in user_message
    assert "[EMAIL_1]" in user_message
    assert "jane@example.com" not in output
    assert "[EMAIL_1]" in output


def test_llm_guardrails_filter_streaming_output_across_chunks() -> None:
    chunks = ["Email str", "eam@example", ".com now"]

    output = llm_guardrails.filter_streaming_output(chunks)

    assert output == ["Email [EMAIL_1] now"]


def test_fastapi_request_filtering_redacts_nested_payload() -> None:
    payload = {
        "message": "Contact jane@example.com",
        "history": [{"content": "SSN 123-45-6789"}],
    }

    safe_payload = fastapi_request_filtering.redact_request_payload(payload)

    assert safe_payload is not payload
    assert "jane@example.com" not in safe_payload["message"]
    assert "[EMAIL_1]" in safe_payload["message"]
    assert "123-45-6789" not in safe_payload["history"][0]["content"]


@pytest.mark.asyncio
async def test_fastapi_middleware_redacts_json_request_body() -> None:
    async def app(scope, receive, send) -> None:
        message = await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": message["body"]})

    middleware = fastapi_request_filtering.DataFogRequestBodyMiddleware(
        app,
        on_detect="redact",
    )
    scope = {
        "type": "http",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"34"),
        ],
    }
    messages = [
        {
            "type": "http.request",
            "body": b'{"email":"jane@example.com"}',
            "more_body": False,
        }
    ]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await middleware(scope, receive, send)

    body = sent[-1]["body"].decode("utf-8")
    assert "jane@example.com" not in body
    assert "[EMAIL_1]" in body


@pytest.mark.asyncio
async def test_fastapi_middleware_blocks_json_request_body() -> None:
    async def app(scope, receive, send) -> None:
        raise AssertionError("blocked requests should not reach the app")

    middleware = fastapi_request_filtering.DataFogRequestBodyMiddleware(
        app,
        on_detect="block",
    )
    scope = {"type": "http", "headers": [(b"content-type", b"application/json")]}
    messages = [
        {
            "type": "http.request",
            "body": b'{"email":"jane@example.com"}',
            "more_body": False,
        }
    ]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await middleware(scope, receive, send)

    assert sent[0]["status"] == 422
    assert b"contains PII" in sent[1]["body"]


def test_logging_filter_redacts_rendered_log_message() -> None:
    record = logging.LogRecord(
        name="example",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Email %s",
        args=("jane@example.com",),
        exc_info=None,
    )
    pii_filter = logging_filter.DataFogPIIFilter()

    assert pii_filter.filter(record) is True
    assert "jane@example.com" not in record.getMessage()
    assert "[EMAIL_1]" in record.getMessage()


def test_langchain_adapter_redacts_runnable_input_and_output() -> None:
    class FakeRunnable:
        def __init__(self) -> None:
            self.received: Any = None

        def invoke(self, input: Any, config: Any | None = None) -> str:
            self.received = input
            return "Send the answer to output@example.com"

    runnable = FakeRunnable()
    adapter = langchain_adapter.DataFogRunnableAdapter(runnable)

    output = adapter.invoke({"question": "Help jane@example.com"})

    assert "jane@example.com" not in runnable.received["question"]
    assert "[EMAIL_1]" in runnable.received["question"]
    assert "output@example.com" not in output
    assert "[EMAIL_1]" in output


def test_llamaindex_adapter_redacts_query_and_response_object() -> None:
    @dataclass
    class FakeResponse:
        response: str

    class FakeQueryEngine:
        def __init__(self) -> None:
            self.received = ""

        def query(self, question: str, **kwargs: Any) -> FakeResponse:
            self.received = question
            return FakeResponse(response="Email answer@example.com")

    query_engine = FakeQueryEngine()
    adapter = llamaindex_adapter.DataFogQueryEngineAdapter(query_engine)

    output = adapter.query("What should jane@example.com do?")

    assert "jane@example.com" not in query_engine.received
    assert "[EMAIL_1]" in query_engine.received
    assert "answer@example.com" not in output
    assert "[EMAIL_1]" in output
