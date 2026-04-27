"""Internal detection/redaction engine boundary for DataFog."""

from __future__ import annotations

import hashlib
import hmac
import os
import warnings
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Optional

from .exceptions import EngineNotAvailable, PolicyViolationError
from .models import (
    Entity,
    PolicyInput,
    RedactResult,
    RedactionPolicy,
    RecognizerInput,
    RegexRecognizer,
    Replacement,
    ScanResult,
    TokenSession,
    ValidationResult,
)
from .models.policy import effective_include_text, get_policy
from .recognizers import get_active_recognizers
from .processing.text_processing.regex_annotator import RegexAnnotator

CANONICAL_TYPE_MAP = {
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
    "DATE_OF_BIRTH": "DATE",
}

ALL_ENTITY_TYPES = {
    "EMAIL",
    "PHONE",
    "SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "DATE",
    "ZIP_CODE",
    "URL",
    "UUID",
    "API_KEY",
    "SECRET",
    "ACCESS_TOKEN",
    "PRIVATE_KEY",
    "PASSWORD",
    "JWT",
    "BEARER_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "SLACK_TOKEN",
    "STRIPE_KEY",
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "ADDRESS",
}

NER_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"}


@dataclass(frozen=True)
class _UnavailableAnnotator:
    """Cached marker used when an optional annotator cannot be initialized."""

    message: str


DEFAULT_SEVERITY = {
    "CREDIT_CARD": "critical",
    "SSN": "critical",
    "API_KEY": "critical",
    "SECRET": "critical",
    "ACCESS_TOKEN": "critical",
    "PRIVATE_KEY": "critical",
    "PASSWORD": "critical",
    "JWT": "critical",
    "BEARER_TOKEN": "critical",
    "AWS_ACCESS_KEY_ID": "critical",
    "GITHUB_TOKEN": "critical",
    "OPENAI_API_KEY": "critical",
    "SLACK_TOKEN": "critical",
    "STRIPE_KEY": "critical",
    "EMAIL": "high",
    "PHONE": "high",
    "IP_ADDRESS": "high",
    "URL": "medium",
    "UUID": "medium",
    "DATE": "low",
    "ZIP_CODE": "medium",
    "PERSON": "medium",
    "ORGANIZATION": "low",
    "LOCATION": "low",
    "ADDRESS": "high",
}

_HMAC_STRATEGIES = {"hmac", "hash", "hmac_sha256"}


def _canonical_type(entity_type: str) -> str:
    normalized = entity_type.upper().strip()
    return CANONICAL_TYPE_MAP.get(normalized, normalized)


def _entity_severity(entity_type: str) -> str:
    return DEFAULT_SEVERITY.get(entity_type, "medium")


def _detector_name(engine: str, entity_type: str) -> str:
    return f"{engine}.{entity_type.lower()}"


def _make_entity(
    *,
    entity_type: str,
    text: str,
    start: int,
    end: int,
    confidence: float,
    engine: str,
    detector: str | None = None,
    validation: ValidationResult | None = None,
) -> Entity:
    canonical_type = _canonical_type(entity_type)
    return Entity(
        type=canonical_type,
        start=start,
        end=end,
        confidence=confidence,
        severity=_entity_severity(canonical_type),  # type: ignore[arg-type]
        detector=detector or _detector_name(engine, canonical_type),
        validation=validation,
        text=text,
    )


def _with_text_mode(entities: list[Entity], *, include_text: bool) -> list[Entity]:
    if include_text:
        return entities
    return [replace(entity, text=None) for entity in entities]


def _normalize_strategy(strategy: str) -> str:
    if strategy in _HMAC_STRATEGIES:
        return "hmac"
    return strategy


def _resolve_hmac_key(hash_key: str | bytes | None) -> bytes:
    resolved = hash_key if hash_key is not None else os.getenv("DATAFOG_HMAC_KEY")
    if resolved is None or resolved == "":
        raise ValueError(
            "Hash strategy requires an HMAC key. Supply hash_key=..., "
            'DATAFOG_HMAC_KEY, or use strategy="token".'
        )
    if isinstance(resolved, bytes):
        return resolved
    return resolved.encode("utf-8")


def _canonicalize_for_hmac(entity_type: str, value: str) -> str:
    normalized = value.strip()
    if entity_type in {"EMAIL", "UUID", "URL"}:
        return normalized.lower()
    if entity_type == "PHONE":
        return "".join(char for char in normalized if char.isdigit() or char == "+")
    return normalized


def _hmac_token(entity_type: str, value: str, hash_key: bytes) -> str:
    canonical_value = _canonicalize_for_hmac(entity_type, value)
    digest = hmac.new(
        hash_key,
        canonical_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:12]
    return f"[{entity_type}_{digest}]"


def _find_all_occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    occurrences: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            break
        end = idx + len(needle)
        occurrences.append((idx, end))
        start = end
    return occurrences


def _entities_from_dict(
    text: str, payload: dict[str, list[str]], engine: str, confidence: float
) -> list[Entity]:
    entities: list[Entity] = []
    value_offsets: dict[str, int] = {}

    for raw_type, values in payload.items():
        canonical_type = _canonical_type(raw_type)
        if canonical_type not in ALL_ENTITY_TYPES:
            continue
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            search_start = value_offsets.get(value, 0)
            idx = text.find(value, search_start)
            if idx < 0:
                idx = text.find(value)
            end = idx + len(value) if idx >= 0 else -1
            value_offsets[value] = end if end >= 0 else search_start + 1
            entities.append(
                _make_entity(
                    entity_type=canonical_type,
                    text=value,
                    start=idx,
                    end=end,
                    confidence=confidence,
                    engine=engine,
                )
            )
    return entities


def _regex_entities(text: str) -> list[Entity]:
    annotator = RegexAnnotator()
    _, structured = annotator.annotate_with_spans(text)
    entities: list[Entity] = []
    for span in structured.spans:
        if not span.text.strip():
            continue
        entities.append(
            _make_entity(
                entity_type=span.label,
                text=span.text,
                start=span.start,
                end=span.end,
                confidence=1.0,
                engine="regex",
            )
        )
    return entities


_INVALID_VALIDATION_STATUSES = {"invalid", "checksum_failed", "parse_failed"}


def _custom_validation(
    recognizer_name: str,
    validator_result: bool | ValidationResult,
) -> ValidationResult | None:
    if isinstance(validator_result, ValidationResult):
        if validator_result.status in _INVALID_VALIDATION_STATUSES:
            return None
        return validator_result
    if validator_result is False:
        return None
    return ValidationResult(validator=recognizer_name, status="valid")


def _custom_entities(
    text: str,
    recognizers: tuple[RegexRecognizer, ...],
) -> list[Entity]:
    entities: list[Entity] = []
    for recognizer in recognizers:
        for match in recognizer.pattern.finditer(text):
            groupdict = match.groupdict()
            if "value" in groupdict and groupdict["value"] is not None:
                start, end = match.span("value")
                value = match.group("value")
            else:
                start, end = match.span(0)
                value = match.group(0)

            if start < 0 or end <= start or not value.strip():
                continue

            validation = None
            if recognizer.validator is not None:
                validation = _custom_validation(
                    recognizer.name,
                    recognizer.validator(value),
                )
                if validation is None:
                    continue

            entities.append(
                _make_entity(
                    entity_type=recognizer.entity_type,
                    text=value,
                    start=start,
                    end=end,
                    confidence=recognizer.confidence,
                    engine="custom",
                    detector=recognizer.detector,
                    validation=validation,
                )
            )
    return entities


def _spacy_entities(text: str) -> list[Entity]:
    annotator = _get_spacy_annotator()
    if isinstance(annotator, _UnavailableAnnotator):
        raise EngineNotAvailable(annotator.message)
    payload = annotator.annotate(text)
    return _entities_from_dict(text, payload, engine="spacy", confidence=0.7)


def _gliner_entities(text: str) -> list[Entity]:
    annotator = _get_gliner_annotator()
    if isinstance(annotator, _UnavailableAnnotator):
        raise EngineNotAvailable(annotator.message)
    payload = annotator.annotate(text)
    return _entities_from_dict(text, payload, engine="gliner", confidence=0.8)


@lru_cache(maxsize=1)
def _get_spacy_annotator():
    try:
        from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
    except ImportError as exc:
        return _UnavailableAnnotator(str(exc))

    try:
        return SpacyPIIAnnotator.create()
    except ImportError as exc:
        return _UnavailableAnnotator(str(exc))
    except Exception as exc:
        return _UnavailableAnnotator(
            f"SpaCy engine initialization failed: {type(exc).__name__}: {exc}"
        )


@lru_cache(maxsize=1)
def _get_gliner_annotator():
    try:
        from .processing.text_processing.gliner_annotator import GLiNERAnnotator
    except ImportError as exc:
        return _UnavailableAnnotator(str(exc))

    try:
        annotator = GLiNERAnnotator.create()
    except ImportError as exc:
        return _UnavailableAnnotator(str(exc))
    except Exception as exc:
        return _UnavailableAnnotator(
            f"GLiNER engine initialization failed: {type(exc).__name__}: {exc}"
        )

    return annotator


def _dedupe_entities(entities: list[Entity]) -> list[Entity]:
    seen: set[tuple[str, str, int, int]] = set()
    deduped: list[Entity] = []
    for entity in sorted(entities, key=lambda e: (e.start, e.end, e.type, e.text)):
        key = (entity.type, entity.text, entity.start, entity.end)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped


def _filter_entity_types(
    entities: list[Entity], entity_types: Optional[list[str]]
) -> list[Entity]:
    if not entity_types:
        return entities
    allowed = {_canonical_type(value) for value in entity_types}
    return [entity for entity in entities if entity.type in allowed]


def _filter_policy(entities: list[Entity], policy: RedactionPolicy) -> list[Entity]:
    return [
        entity
        for entity in entities
        if policy.allows_entity(entity.type, entity.confidence)
    ]


def _needs_ner(entity_types: Optional[list[str]]) -> bool:
    if entity_types is None:
        return True
    requested = {_canonical_type(value) for value in entity_types}
    return bool(requested & NER_ENTITY_TYPES)


def scan(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
    include_text: bool = False,
    locale: str = "global",
    policy_name: str | None = None,
    policy: PolicyInput = None,
    recognizers: Optional[list[RecognizerInput]] = None,
) -> ScanResult:
    """Scan text for PII entities."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if engine not in {"regex", "spacy", "gliner", "smart"}:
        raise ValueError("engine must be one of: regex, spacy, gliner, smart")

    resolved_policy = get_policy(policy)
    include_text = effective_include_text(include_text, resolved_policy)
    effective_locale = (
        resolved_policy.locale
        if locale == "global" and resolved_policy.locale != "global"
        else locale
    )
    effective_policy_name = policy_name or resolved_policy.name

    active_recognizers = get_active_recognizers(recognizers)
    custom_entities = _custom_entities(text, active_recognizers)
    regex_entities = _regex_entities(text)
    engines_used = {"regex"}
    if active_recognizers:
        engines_used.add("custom")

    if engine == "regex":
        filtered = _filter_policy(
            _filter_entity_types(regex_entities + custom_entities, entity_types),
            resolved_policy,
        )
        return ScanResult(
            entities=_with_text_mode(
                _dedupe_entities(filtered),
                include_text=include_text,
            ),
            input_length=len(text),
            engine="+".join(sorted(engines_used)),
            locale=effective_locale,
            policy_name=effective_policy_name,
            include_text=include_text,
        )

    combined: list[Entity] = list(regex_entities + custom_entities)

    if engine == "spacy" and _needs_ner(entity_types):
        try:
            spacy_entities = _spacy_entities(text)
            combined.extend(spacy_entities)
            engines_used.add("spacy")
        except EngineNotAvailable:
            if engine == "spacy":
                raise
            warnings.warn(
                "SpaCy not available, smart scan continuing without spaCy. "
                "Install with: pip install datafog[nlp]",
                UserWarning,
                stacklevel=2,
            )

    if engine == "gliner" and _needs_ner(entity_types):
        try:
            gliner_entities = _gliner_entities(text)
            combined.extend(gliner_entities)
            engines_used.add("gliner")
        except EngineNotAvailable:
            if engine == "gliner":
                raise
            warnings.warn(
                "GLiNER not available, smart scan continuing without GLiNER. "
                "Install with: pip install datafog[nlp-advanced]",
                UserWarning,
                stacklevel=2,
            )

    if engine == "smart" and _needs_ner(entity_types):
        try:
            gliner_entities = _gliner_entities(text)
            combined.extend(gliner_entities)
            engines_used.add("gliner")
        except EngineNotAvailable:
            warnings.warn(
                "GLiNER not available, smart scan falling back to spaCy. "
                "Install with: pip install datafog[nlp-advanced]",
                UserWarning,
                stacklevel=2,
            )
            try:
                spacy_entities = _spacy_entities(text)
                combined.extend(spacy_entities)
                engines_used.add("spacy")
            except EngineNotAvailable:
                warnings.warn(
                    "SpaCy not available, smart scan continuing with regex only. "
                    "Install with: pip install datafog[nlp]",
                    UserWarning,
                    stacklevel=2,
                )

    filtered = _filter_policy(
        _filter_entity_types(combined, entity_types),
        resolved_policy,
    )
    deduped = _dedupe_entities(filtered)
    return ScanResult(
        entities=_with_text_mode(deduped, include_text=include_text),
        input_length=len(text),
        engine="+".join(sorted(engines_used)),
        locale=effective_locale,
        policy_name=effective_policy_name,
        include_text=include_text,
    )


def redact(
    text: str,
    entities: list[Entity],
    strategy: str | None = None,
    policy_name: str | None = None,
    include_text: bool = False,
    session: TokenSession | None = None,
    hash_key: str | bytes | None = None,
    policy: PolicyInput = None,
) -> RedactResult:
    """Redact PII entities from text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    resolved_policy = get_policy(policy)
    include_text = effective_include_text(include_text, resolved_policy)
    base_strategy = _normalize_strategy(strategy or resolved_policy.default_action)
    if base_strategy not in {
        "token",
        "mask",
        "hmac",
        "pseudonymize",
        "drop",
        "block",
        "warn",
    }:
        raise ValueError(
            "strategy must be one of: token, mask, hmac, hash, pseudonymize, drop, block, warn"
        )

    resolved_hash_key: bytes | None = None

    def _get_resolved_hash_key() -> bytes:
        nonlocal resolved_hash_key
        if resolved_hash_key is None:
            resolved_hash_key = _resolve_hmac_key(hash_key)
        return resolved_hash_key

    if base_strategy == "hmac":
        _get_resolved_hash_key()

    counters: dict[str, int] = {}
    pseudonym_by_value: dict[tuple[str, str], str] = {}

    valid_entities = [
        entity
        for entity in entities
        if 0 <= entity.start < entity.end <= len(text)
        and resolved_policy.allows_entity(entity.type, entity.confidence)
    ]
    sorted_entities = sorted(valid_entities, key=lambda e: (e.start, e.end))

    selected_entities: list[Entity] = []
    cursor = 0
    for entity in sorted_entities:
        if entity.start < cursor:
            continue
        selected_entities.append(entity)
        cursor = entity.end

    output_parts: list[str] = []
    replacements: list[Replacement] = []
    source_cursor = 0
    output_cursor = 0

    for entity_index, entity in enumerate(selected_entities):
        original = text[entity.start : entity.end]
        entity_policy = resolved_policy.policy_for(entity.type)
        action = _normalize_strategy(
            entity_policy.action
            if entity_policy is not None and entity_policy.action is not None
            else base_strategy
        )

        if action == "block":
            raise PolicyViolationError(
                f"Policy {resolved_policy.name!r} blocked {entity.type} detection."
            )

        if action == "mask":
            replacement = "*" * max(len(original), 1)
            replacement_metadata = replacement
            replacement_action = "mask"
        elif action == "hmac":
            replacement = _hmac_token(entity.type, original, _get_resolved_hash_key())
            replacement_metadata = replacement
            replacement_action = "hmac"
        elif action == "pseudonymize":
            key = (entity.type, original)
            if key not in pseudonym_by_value:
                counters[entity.type] = counters.get(entity.type, 0) + 1
                pseudonym_by_value[key] = (
                    f"[{entity.type}_PSEUDO_{counters[entity.type]}]"
                )
            replacement = pseudonym_by_value[key]
            replacement_metadata = replacement
            replacement_action = "token"
        elif action == "drop":
            replacement = ""
            replacement_metadata = ""
            replacement_action = "drop"
        elif action == "warn":
            replacement = original
            replacement_metadata = None
            replacement_action = "warn"
        else:  # token
            if resolved_policy.mapping_mode == "session" and session is None:
                raise ValueError(
                    "Policy mapping_mode='session' requires an explicit TokenSession."
                )
            if session is not None:
                replacement = session._token_for(entity.type, original)
            else:
                counters[entity.type] = counters.get(entity.type, 0) + 1
                replacement = f"[{entity.type}_{counters[entity.type]}]"
            replacement_metadata = replacement
            replacement_action = "token"

        unchanged = text[source_cursor : entity.start]
        output_parts.append(unchanged)
        output_cursor += len(unchanged)

        replacement_start = output_cursor
        replacement_end = replacement_start + len(replacement)
        output_parts.append(replacement)
        output_cursor = replacement_end

        replacements.append(
            Replacement(
                entity_index=entity_index,
                action=replacement_action,
                original_start=entity.start,
                original_end=entity.end,
                replacement_start=replacement_start,
                replacement_end=replacement_end,
                replacement=replacement_metadata,
                token=replacement if replacement.startswith("[") else None,
            )
        )
        source_cursor = entity.end

    output_parts.append(text[source_cursor:])
    redacted_text = "".join(output_parts)
    return RedactResult(
        redacted_text=redacted_text,
        entities=_with_text_mode(selected_entities, include_text=include_text),
        replacements=replacements,
        policy_name=policy_name or resolved_policy.name,
        session_id=session.session_id if session is not None else None,
    )


def restore(text: str, session: TokenSession) -> str:
    """Restore text from an in-memory token session."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(session, TokenSession):
        raise TypeError("session must be a TokenSession")
    return session._restore(text)


def scan_and_redact(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
    strategy: str | None = None,
    locale: str = "global",
    policy_name: str | None = None,
    include_text: bool = False,
    session: TokenSession | None = None,
    hash_key: str | bytes | None = None,
    policy: PolicyInput = None,
    recognizers: Optional[list[RecognizerInput]] = None,
) -> RedactResult:
    """Convenience wrapper: scan then redact."""
    scan_result = scan(
        text=text,
        engine=engine,
        entity_types=entity_types,
        include_text=include_text,
        locale=locale,
        policy_name=policy_name,
        policy=policy,
        recognizers=recognizers,
    )
    return redact(
        text=text,
        entities=scan_result.entities,
        strategy=strategy,
        policy_name=policy_name,
        include_text=include_text,
        session=session,
        hash_key=hash_key,
        policy=policy,
    )
