"""FastAPI request filtering and middleware recipes for DataFog v5.

The ASGI middleware and redaction helpers are dependency-free and tested
without FastAPI. The ``create_app`` function imports FastAPI only when you run
the example app.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import datafog

from .utils import redact_nested

ASGIApp = Callable[
    [
        dict[str, Any],
        Callable[[], Awaitable[dict[str, Any]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def redact_request_payload(
    payload: dict[str, Any],
    *,
    guardrail: datafog.Guardrail | None = None,
) -> dict[str, Any]:
    """Return a redacted copy of a JSON request payload."""
    return redact_nested(payload, guardrail=guardrail)


class DataFogRequestBodyMiddleware:
    """ASGI middleware that blocks or redacts JSON/text request bodies.

    Use it with FastAPI via ``app.add_middleware(DataFogRequestBodyMiddleware)``.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        guardrail: datafog.Guardrail | None = None,
        on_detect: str = "block",
        content_types: tuple[str, ...] = ("application/json", "text/plain"),
    ) -> None:
        if on_detect not in {"block", "redact", "warn"}:
            raise ValueError("on_detect must be one of: block, redact, warn")
        self.app = app
        self.guardrail = guardrail or datafog.create_guardrail(
            engine="regex",
            policy="llm",
        )
        self.on_detect = on_detect
        self.content_types = content_types

    async def __call__(
        self, scope: dict[str, Any], receive: Receive, send: Send
    ) -> None:
        if scope.get("type") != "http" or not self._should_filter(scope):
            await self.app(scope, receive, send)
            return

        messages = await self._collect_request_messages(receive)
        body = b"".join(message.get("body", b"") for message in messages)
        body_text = body.decode("utf-8", errors="replace")
        scan_result = self.guardrail.scan(body_text)
        if not scan_result.entities:
            await self.app(scope, _replay_receive(messages), send)
            return

        if self.on_detect == "block":
            await _send_json_response(
                send,
                422,
                {"detail": "Request body contains PII."},
            )
            return

        if self.on_detect == "redact":
            safe_body = self.guardrail.filter(body_text).redacted_text.encode("utf-8")
            safe_scope = _scope_with_content_length(scope, len(safe_body))
            await self.app(
                safe_scope,
                _replay_receive(
                    [{"type": "http.request", "body": safe_body, "more_body": False}]
                ),
                send,
            )
            return

        await self.app(scope, _replay_receive(messages), send)

    def _should_filter(self, scope: dict[str, Any]) -> bool:
        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
            if isinstance(key, bytes) and isinstance(value, bytes)
        }
        content_type = headers.get(b"content-type", b"").decode("latin1").lower()
        return any(expected in content_type for expected in self.content_types)

    @staticmethod
    async def _collect_request_messages(receive: Receive) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") != "http.request" or not message.get("more_body"):
                return messages


def _replay_receive(messages: list[dict[str, Any]]) -> Receive:
    remaining = list(messages)

    async def receive() -> dict[str, Any]:
        if remaining:
            return remaining.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


def _scope_with_content_length(
    scope: dict[str, Any], content_length: int
) -> dict[str, Any]:
    headers = [
        (key, value)
        for key, value in scope.get("headers", [])
        if key.lower() != b"content-length"
    ]
    headers.append((b"content-length", str(content_length).encode("ascii")))
    return {**scope, "headers": headers}


async def _send_json_response(
    send: Send,
    status: int,
    payload: dict[str, Any],
) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def create_app():
    """Create a tiny FastAPI app that redacts JSON before application logic."""
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError(
            "Install FastAPI support with: pip install datafog[web]"
        ) from exc

    app = FastAPI()
    guardrail = datafog.create_guardrail(engine="regex", policy="llm")
    app.add_middleware(
        DataFogRequestBodyMiddleware,
        guardrail=guardrail,
        on_detect="redact",
    )

    @app.post("/chat")
    async def chat(payload: dict[str, Any]) -> dict[str, Any]:
        safe_payload = redact_request_payload(payload, guardrail=guardrail)
        return {
            "safe_payload": safe_payload,
            "message": "Send safe_payload to your model or service.",
        }

    return app


app = None

if __name__ == "__main__":
    app = create_app()
