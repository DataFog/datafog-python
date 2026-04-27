"""Python logging filter that redacts PII before records are emitted."""

from __future__ import annotations

import logging

import datafog


class DataFogPIIFilter(logging.Filter):
    """Redact the rendered log message while preserving normal log flow."""

    def __init__(self, *, guardrail: datafog.Guardrail | None = None) -> None:
        super().__init__()
        self.guardrail = guardrail or datafog.create_guardrail(
            engine="regex",
            policy="logs",
            strategy="token",
        )

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.guardrail.filter(record.getMessage()).redacted_text
        record.args = ()
        return True


def configure_safe_logging(logger: logging.Logger | None = None) -> logging.Logger:
    """Attach the DataFog filter to a logger."""
    active_logger = logger or logging.getLogger("datafog.example")
    active_logger.addFilter(DataFogPIIFilter())
    return active_logger


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log = configure_safe_logging()
    log.info("Customer email is %s", "jane@example.com")
