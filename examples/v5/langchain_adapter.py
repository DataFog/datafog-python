"""LangChain-style adapter pattern without importing LangChain."""

from __future__ import annotations

from typing import Any

import datafog

from .utils import redact_nested, redact_text


class DataFogRunnableAdapter:
    """Wrap an object with ``invoke`` and redact inputs/outputs around it."""

    def __init__(
        self,
        runnable: Any,
        *,
        guardrail: datafog.Guardrail | None = None,
    ) -> None:
        self.runnable = runnable
        self.guardrail = guardrail or datafog.create_guardrail(
            engine="regex",
            policy="llm",
        )

    def invoke(self, input: Any, config: Any | None = None) -> Any:
        """Invoke the wrapped runnable with redacted inputs and outputs."""
        safe_input = redact_nested(input, guardrail=self.guardrail)
        if config is None:
            output = self.runnable.invoke(safe_input)
        else:
            output = self.runnable.invoke(safe_input, config=config)
        if isinstance(output, str):
            return redact_text(output, guardrail=self.guardrail)
        return redact_nested(output, guardrail=self.guardrail)


if __name__ == "__main__":

    class EchoRunnable:
        def invoke(self, input: Any, config: Any | None = None) -> str:
            return f"received: {input}"

    chain = DataFogRunnableAdapter(EchoRunnable())
    print(chain.invoke({"question": "Email jane@example.com"}))
