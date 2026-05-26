"""Agent-oriented API helpers for LLM application guardrails."""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterator, Optional, TypeVar

from .engine import Entity, RedactResult, ScanResult, scan, scan_and_redact

F = TypeVar("F", bound=Callable[..., Any])


class GuardrailBlockedError(RuntimeError):
    """Raised when a guardrail is configured to block and PII is detected."""


@dataclass
class GuardrailWatch:
    """Context helper for manually applying a guardrail to text values."""

    guardrail: "Guardrail"
    detections: int = 0
    redactions: int = 0

    def scan(self, text: str) -> ScanResult:
        """Scan text and increment detection counters."""
        result = self.guardrail.scan(text)
        if result.entities:
            self.detections += len(result.entities)
        return result

    def filter(self, text: str) -> RedactResult:
        """Filter text according to guardrail behavior and increment counters."""
        result = self.guardrail.filter(text)
        if result.entities:
            self.detections += len(result.entities)
        if result.redacted_text != text:
            self.redactions += 1
        return result


@dataclass
class Guardrail:
    """Reusable text guardrail for wrapping LLM prompts and outputs."""

    entity_types: Optional[list[str]] = None
    locales: Optional[list[str]] = None
    engine: str = "regex"
    strategy: str = "token"
    on_detect: str = "redact"

    def __post_init__(self) -> None:
        if self.on_detect not in {"redact", "block", "warn"}:
            raise ValueError("on_detect must be one of: redact, block, warn")

    def scan(self, text: str) -> ScanResult:
        """Scan a text value for entities."""
        return scan(
            text=text,
            engine=self.engine,
            entity_types=self.entity_types,
            locales=self.locales,
        )

    def filter(self, text: str) -> RedactResult:
        """Scan then enforce configured behavior."""
        result = scan_and_redact(
            text=text,
            engine=self.engine,
            entity_types=self.entity_types,
            strategy=self.strategy,
            locales=self.locales,
        )
        if not result.entities:
            return result

        if self.on_detect == "block":
            raise GuardrailBlockedError(
                f"Guardrail blocked text containing {len(result.entities)} PII entities."
            )
        if self.on_detect == "warn":
            warnings.warn(
                f"Guardrail detected {len(result.entities)} PII entities.",
                UserWarning,
                stacklevel=2,
            )
            return RedactResult(
                redacted_text=text,
                mapping={},
                entities=result.entities,
            )

        return result

    def __call__(self, fn: F) -> F:
        """Decorator that applies guardrail filtering to string return values."""

        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            output = fn(*args, **kwargs)
            if isinstance(output, str):
                return self.filter(output).redacted_text
            return output

        return wrapped  # type: ignore[return-value]

    @contextmanager
    def watch(self) -> Iterator[GuardrailWatch]:
        """Context manager for explicit guardrail checks."""
        watcher = GuardrailWatch(guardrail=self)
        yield watcher


def sanitize(text: str, engine: str = "regex", **kwargs: Any) -> str:
    """
    One-liner PII removal.

    Returns the redacted text only.
    """
    result = scan_and_redact(text=text, engine=engine, **kwargs)
    return result.redacted_text


def scan_prompt(prompt: str, engine: str = "regex", **kwargs: Any) -> ScanResult:
    """
    Scan an LLM prompt for PII without modifying the input text.
    """
    return scan(prompt, engine=engine, **kwargs)


def filter_output(output: str, engine: str = "regex", **kwargs: Any) -> RedactResult:
    """
    Scan and redact PII from model output before returning to users.
    """
    return scan_and_redact(output, engine=engine, **kwargs)


def create_guardrail(
    entity_types: Optional[list[str]] = None,
    locales: Optional[list[str]] = None,
    engine: str = "regex",
    strategy: str = "token",
    on_detect: str = "redact",
) -> Guardrail:
    """
    Create a reusable guardrail object for wrapping LLM calls.
    """
    return Guardrail(
        entity_types=entity_types,
        locales=locales,
        engine=engine,
        strategy=strategy,
        on_detect=on_detect,
    )


__all__ = [
    "Entity",
    "ScanResult",
    "RedactResult",
    "Guardrail",
    "GuardrailWatch",
    "GuardrailBlockedError",
    "sanitize",
    "scan_prompt",
    "filter_output",
    "create_guardrail",
]
