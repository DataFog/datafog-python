"""Public result models for the v5 DataFog API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

ValidationStatus = Literal[
    "valid",
    "invalid",
    "unknown",
    "not_applicable",
    "region_required",
    "checksum_failed",
    "parse_failed",
]

Severity = Literal["low", "medium", "high", "critical"]
RedactionAction = Literal["token", "mask", "hmac", "drop", "block", "warn"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation metadata for a detected entity."""

    validator: str
    status: ValidationStatus
    reason: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "validator": self.validator,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class Entity:
    """A detected PII or secret-like entity."""

    type: str
    start: int
    end: int
    confidence: float
    severity: Severity
    detector: str
    validation: ValidationResult | None = None
    text: str | None = None

    @property
    def engine(self) -> str:
        """Compatibility alias for older code that expected ``entity.engine``."""
        return self.detector.split(".", 1)[0]

    def to_dict(self, *, include_text: bool = False) -> dict[str, object]:
        return {
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "severity": self.severity,
            "detector": self.detector,
            "validation": (
                self.validation.to_dict() if self.validation is not None else None
            ),
            "text": self.text if include_text else None,
        }

    def to_safe_dict(self) -> dict[str, object]:
        return self.to_dict(include_text=False)

    def to_json(self, *, include_text: bool = False) -> str:
        return json.dumps(self.to_dict(include_text=include_text))

    def to_safe_json(self) -> str:
        return self.to_json(include_text=False)


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Result of scanning text for PII."""

    entities: list[Entity]
    input_length: int
    engine: str
    locale: str
    policy_name: str | None = None
    include_text: bool = False

    @property
    def engine_used(self) -> str:
        """Compatibility alias for the v4.4 preview result field."""
        return self.engine

    def to_dict(self, *, include_text: bool = False) -> dict[str, object]:
        return {
            "entities": [
                entity.to_dict(include_text=include_text) for entity in self.entities
            ],
            "input_length": self.input_length,
            "engine": self.engine,
            "locale": self.locale,
            "policy_name": self.policy_name,
            "include_text": include_text,
        }

    def to_safe_dict(self) -> dict[str, object]:
        return self.to_dict(include_text=False)

    def to_json(self, *, include_text: bool = False) -> str:
        return json.dumps(self.to_dict(include_text=include_text))

    def to_safe_json(self) -> str:
        return self.to_json(include_text=False)


@dataclass(frozen=True, slots=True)
class Replacement:
    """Safe redaction replacement metadata."""

    entity_index: int
    action: RedactionAction
    original_start: int
    original_end: int
    replacement_start: int
    replacement_end: int
    replacement: str | None = None
    token: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_index": self.entity_index,
            "action": self.action,
            "original_start": self.original_start,
            "original_end": self.original_end,
            "replacement_start": self.replacement_start,
            "replacement_end": self.replacement_end,
            "replacement": self.replacement,
            "token": self.token,
        }


@dataclass(frozen=True, slots=True)
class RedactResult:
    """Result of redacting PII from text."""

    redacted_text: str
    entities: list[Entity]
    replacements: list[Replacement]
    policy_name: str | None = None
    session_id: str | None = None

    def to_dict(self, *, include_text: bool = False) -> dict[str, object]:
        return {
            "redacted_text": self.redacted_text,
            "entities": [
                entity.to_dict(include_text=include_text) for entity in self.entities
            ],
            "replacements": [
                replacement.to_dict() for replacement in self.replacements
            ],
            "policy_name": self.policy_name,
            "session_id": self.session_id,
        }

    def to_safe_dict(self) -> dict[str, object]:
        return self.to_dict(include_text=False)

    def to_json(self, *, include_text: bool = False) -> str:
        return json.dumps(self.to_dict(include_text=include_text))

    def to_safe_json(self) -> str:
        return self.to_json(include_text=False)


@dataclass(slots=True)
class TokenSession:
    """In-memory reversible token session metadata."""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    token_scope: Literal["value", "occurrence"] = "value"
    token_prefix: str = "DF"
    _token_to_value: dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _value_to_token: dict[tuple[str, str], str] = field(
        default_factory=dict, init=False, repr=False
    )
    _counters: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    @property
    def mapping_count(self) -> int:
        return len(self._token_to_value)

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "token_scope": self.token_scope,
            "token_prefix": self.token_prefix,
            "mapping_count": self.mapping_count,
        }

    def clear(self) -> None:
        self._token_to_value.clear()
        self._value_to_token.clear()
        self._counters.clear()

    def _token_for(self, entity_type: str, value: str) -> str:
        key = (entity_type, value)
        if self.token_scope == "value":
            existing = self._value_to_token.get(key)
            if existing is not None:
                return existing

        self._counters[entity_type] = self._counters.get(entity_type, 0) + 1
        token = f"[{self.token_prefix}_{entity_type}_{self._counters[entity_type]}]"
        self._token_to_value[token] = value
        if self.token_scope == "value":
            self._value_to_token[key] = token
        return token

    def _restore(self, text: str) -> str:
        restored = text
        for token, value in sorted(
            self._token_to_value.items(), key=lambda item: len(item[0]), reverse=True
        ):
            restored = restored.replace(token, value)
        return restored


__all__ = [
    "Entity",
    "RedactResult",
    "Replacement",
    "ScanResult",
    "Severity",
    "TokenSession",
    "ValidationResult",
    "ValidationStatus",
]
