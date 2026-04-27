"""Custom recognizer models for the v5 DataFog API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Pattern

from .policy import canonical_entity_type
from .results import ValidationResult

RecognizerValidator = Callable[[str], bool | ValidationResult]


@dataclass(frozen=True, slots=True)
class RegexRecognizer:
    """User-defined regex recognizer for domain-specific PII and secrets."""

    entity_type: str
    pattern: str | Pattern[str]
    confidence: float = 0.85
    description: str | None = None
    name: str | None = None
    validator: RecognizerValidator | None = None
    flags: int = 0

    def __post_init__(self) -> None:
        canonical_type = canonical_entity_type(self.entity_type)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("recognizer confidence must be between 0.0 and 1.0")

        compiled = (
            re.compile(self.pattern, self.flags)
            if isinstance(self.pattern, str)
            else self.pattern
        )
        name = self.name or canonical_type.lower()
        normalized_name = name.strip().lower().replace(" ", "_")
        if not normalized_name:
            raise ValueError("recognizer name must not be empty")

        object.__setattr__(self, "entity_type", canonical_type)
        object.__setattr__(self, "pattern", compiled)
        object.__setattr__(self, "name", normalized_name)

    @property
    def detector(self) -> str:
        return f"custom.{self.name}"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "description": self.description,
            "detector": self.detector,
        }


RecognizerInput = RegexRecognizer | dict[str, object]


def coerce_recognizer(recognizer: RecognizerInput) -> RegexRecognizer:
    """Convert supported recognizer inputs into a RegexRecognizer."""
    if isinstance(recognizer, RegexRecognizer):
        return recognizer
    if isinstance(recognizer, dict):
        return RegexRecognizer(**recognizer)
    raise TypeError("recognizers must be RegexRecognizer objects or dictionaries")


__all__ = [
    "RecognizerInput",
    "RecognizerValidator",
    "RegexRecognizer",
    "coerce_recognizer",
]
