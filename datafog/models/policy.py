"""Policy models for the v5 DataFog API."""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PolicyAction = Literal["token", "mask", "hmac", "drop", "block", "warn"]
RawTextMode = Literal["allow", "deny"]
MappingMode = Literal["none", "session"]

_CANONICAL_TYPE_MAP = {
    "DOB": "DATE",
    "ZIP": "ZIP_CODE",
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "ADDRESS",
    "PHONE_NUMBER": "PHONE",
    "SOCIAL_SECURITY_NUMBER": "SSN",
    "CREDIT_CARD_NUMBER": "CREDIT_CARD",
}

_DISABLE_RAW_TEXT_VALUES = {"1", "true", "yes", "on"}


def canonical_entity_type(entity_type: str) -> str:
    """Return DataFog's canonical uppercase entity type."""
    normalized = entity_type.upper().strip()
    return _CANONICAL_TYPE_MAP.get(normalized, normalized)


class EntityPolicy(BaseModel):
    """Per-entity policy overrides."""

    model_config = ConfigDict(frozen=True)

    action: PolicyAction | None = None
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled: bool = True


class RedactionPolicy(BaseModel):
    """Validated policy/config boundary for scan and redaction behavior."""

    model_config = ConfigDict(frozen=True)

    name: str = "default"
    default_action: PolicyAction = "token"
    entity_types: frozenset[str] | None = None
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    locale: str = "global"
    phone_region: str | None = None
    raw_text_mode: RawTextMode = "allow"
    mapping_mode: MappingMode = "none"
    entities: dict[str, EntityPolicy] = Field(default_factory=dict)

    @field_validator("entity_types", mode="before")
    @classmethod
    def _canonicalize_entity_types(cls, value: Any):
        if value is None:
            return None
        return frozenset(canonical_entity_type(str(item)) for item in value)

    @field_validator("entities", mode="before")
    @classmethod
    def _canonicalize_entity_policy_keys(cls, value: Any):
        if value is None:
            return {}
        return {
            canonical_entity_type(str(entity_type)): entity_policy
            for entity_type, entity_policy in dict(value).items()
        }

    @field_validator("locale")
    @classmethod
    def _normalize_locale(cls, value: str) -> str:
        normalized = value.lower().strip()
        if not normalized:
            raise ValueError("locale must not be empty")
        return normalized

    @field_validator("phone_region")
    @classmethod
    def _normalize_phone_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper().strip()
        return normalized or None

    def policy_for(self, entity_type: str) -> EntityPolicy | None:
        return self.entities.get(canonical_entity_type(entity_type))

    def allows_entity(self, entity_type: str, confidence: float) -> bool:
        canonical_type = canonical_entity_type(entity_type)
        if self.entity_types is not None and canonical_type not in self.entity_types:
            return False

        entity_policy = self.policy_for(canonical_type)
        if entity_policy is not None and not entity_policy.enabled:
            return False

        threshold = (
            entity_policy.threshold
            if entity_policy is not None and entity_policy.threshold is not None
            else self.threshold
        )
        return confidence >= threshold

    def action_for(self, entity_type: str) -> PolicyAction:
        entity_policy = self.policy_for(entity_type)
        if entity_policy is not None and entity_policy.action is not None:
            return entity_policy.action
        return self.default_action

    def allows_raw_text(self) -> bool:
        return self.raw_text_mode != "deny"

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "default_action": self.default_action,
            "entity_types": (
                sorted(self.entity_types) if self.entity_types is not None else None
            ),
            "threshold": self.threshold,
            "locale": self.locale,
            "phone_region": self.phone_region,
            "raw_text_mode": self.raw_text_mode,
            "mapping_mode": self.mapping_mode,
            "entities": {
                entity_type: entity_policy.model_dump()
                for entity_type, entity_policy in sorted(self.entities.items())
            },
        }


POLICY_PRESETS: dict[str, RedactionPolicy] = {
    "default": RedactionPolicy(name="default", default_action="token"),
    "llm": RedactionPolicy(
        name="llm",
        default_action="token",
        raw_text_mode="deny",
    ),
    "logs": RedactionPolicy(
        name="logs",
        default_action="hmac",
        raw_text_mode="deny",
    ),
    "strict": RedactionPolicy(
        name="strict",
        default_action="block",
        raw_text_mode="deny",
    ),
    "dataset": RedactionPolicy(
        name="dataset",
        default_action="mask",
        raw_text_mode="deny",
    ),
}

PolicyInput = RedactionPolicy | str | dict[str, Any] | None


def get_policy(
    policy: PolicyInput = None,
    *,
    preset: str | None = None,
) -> RedactionPolicy:
    """Resolve a policy object, policy dict, or built-in preset name."""
    if policy is not None and preset is not None:
        raise ValueError("Specify either policy or preset, not both.")

    selected = preset if preset is not None else policy
    if selected is None:
        return POLICY_PRESETS["default"]
    if isinstance(selected, RedactionPolicy):
        return selected
    if isinstance(selected, str):
        try:
            return POLICY_PRESETS[selected]
        except KeyError as exc:
            allowed = ", ".join(sorted(POLICY_PRESETS))
            raise ValueError(f"policy preset must be one of: {allowed}") from exc
    return RedactionPolicy.model_validate(selected)


def raw_text_globally_disabled() -> bool:
    """Return whether environment config denies raw text everywhere."""
    return os.getenv("DATAFOG_DISABLE_RAW_TEXT", "").lower() in _DISABLE_RAW_TEXT_VALUES


def effective_include_text(include_text: bool, policy: RedactionPolicy) -> bool:
    """Apply v5 raw text precedence: global deny, policy deny, per-call opt-in."""
    if raw_text_globally_disabled():
        return False
    if not policy.allows_raw_text():
        return False
    return include_text


__all__ = [
    "EntityPolicy",
    "MappingMode",
    "POLICY_PRESETS",
    "PolicyAction",
    "PolicyInput",
    "RawTextMode",
    "RedactionPolicy",
    "canonical_entity_type",
    "effective_include_text",
    "get_policy",
    "raw_text_globally_disabled",
]
