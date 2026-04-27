"""Global custom recognizer registry for DataFog."""

from __future__ import annotations

from threading import RLock
from typing import Iterable

from .models.recognizers import (
    RecognizerInput,
    RecognizerValidator,
    RegexRecognizer,
    coerce_recognizer,
)

_REGISTRY_LOCK = RLock()
_GLOBAL_RECOGNIZERS: list[RegexRecognizer] = []


def register_recognizer(recognizer: RecognizerInput) -> RegexRecognizer:
    """Register a custom recognizer globally and return the normalized object."""
    normalized = coerce_recognizer(recognizer)
    with _REGISTRY_LOCK:
        _GLOBAL_RECOGNIZERS.append(normalized)
    return normalized


def register_regex_recognizer(
    *,
    entity_type: str,
    pattern: str,
    confidence: float = 0.85,
    description: str | None = None,
    name: str | None = None,
    validator: RecognizerValidator | None = None,
    flags: int = 0,
) -> RegexRecognizer:
    """Create and globally register a regex recognizer."""
    return register_recognizer(
        RegexRecognizer(
            entity_type=entity_type,
            pattern=pattern,
            confidence=confidence,
            description=description,
            name=name,
            validator=validator,
            flags=flags,
        )
    )


def list_recognizers() -> tuple[RegexRecognizer, ...]:
    """Return globally registered custom recognizers."""
    with _REGISTRY_LOCK:
        return tuple(_GLOBAL_RECOGNIZERS)


def clear_recognizers() -> None:
    """Clear globally registered custom recognizers."""
    with _REGISTRY_LOCK:
        _GLOBAL_RECOGNIZERS.clear()


def get_active_recognizers(
    recognizers: Iterable[RecognizerInput] | None = None,
) -> tuple[RegexRecognizer, ...]:
    """Return global recognizers plus per-call recognizers."""
    active = list(list_recognizers())
    if recognizers is not None:
        active.extend(coerce_recognizer(recognizer) for recognizer in recognizers)
    return tuple(active)


__all__ = [
    "clear_recognizers",
    "get_active_recognizers",
    "list_recognizers",
    "register_recognizer",
    "register_regex_recognizer",
]
