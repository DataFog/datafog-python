"""LlamaIndex-style query engine adapter without importing LlamaIndex."""

from __future__ import annotations

from typing import Any

import datafog

from .utils import redact_text


class DataFogQueryEngineAdapter:
    """Wrap an object with ``query`` and redact questions/responses around it."""

    def __init__(
        self,
        query_engine: Any,
        *,
        guardrail: datafog.Guardrail | None = None,
    ) -> None:
        self.query_engine = query_engine
        self.guardrail = guardrail or datafog.create_guardrail(
            engine="regex",
            policy="llm",
        )

    def query(self, question: str, **kwargs: Any) -> str:
        """Query the wrapped engine without exposing raw PII."""
        safe_question = redact_text(question, guardrail=self.guardrail)
        response = self.query_engine.query(safe_question, **kwargs)
        return redact_text(_response_text(response), guardrail=self.guardrail)


def _response_text(response: Any) -> str:
    response_text = getattr(response, "response", None)
    if isinstance(response_text, str):
        return response_text
    return str(response)


if __name__ == "__main__":

    class EchoQueryEngine:
        def query(self, question: str, **kwargs: Any) -> str:
            return f"answer for: {question}"

    engine = DataFogQueryEngineAdapter(EchoQueryEngine())
    print(engine.query("Does jane@example.com have an open ticket?"))
