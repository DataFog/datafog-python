"""Internal detection/redaction engine boundary for DataFog."""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from .exceptions import EngineNotAvailable
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
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "ADDRESS",
}

NER_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"}


@dataclass
class Entity:
    """A detected PII entity."""

    type: str
    text: str
    start: int
    end: int
    confidence: float
    engine: str


@dataclass
class ScanResult:
    """Result of scanning text for PII."""

    entities: list[Entity]
    text: str
    engine_used: str


@dataclass
class RedactResult:
    """Result of redacting PII from text."""

    redacted_text: str
    mapping: dict[str, str]
    entities: list[Entity]


def _canonical_type(entity_type: str) -> str:
    normalized = entity_type.upper().strip()
    return CANONICAL_TYPE_MAP.get(normalized, normalized)


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
                Entity(
                    type=canonical_type,
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
            Entity(
                type=_canonical_type(span.label),
                text=span.text,
                start=span.start,
                end=span.end,
                confidence=1.0,
                engine="regex",
            )
        )
    return entities


def _spacy_entities(text: str) -> list[Entity]:
    annotator = _get_spacy_annotator()
    payload = annotator.annotate(text)
    return _entities_from_dict(text, payload, engine="spacy", confidence=0.7)


def _gliner_entities(text: str) -> list[Entity]:
    annotator = _get_gliner_annotator()
    payload = annotator.annotate(text)
    return _entities_from_dict(text, payload, engine="gliner", confidence=0.8)


@lru_cache(maxsize=1)
def _get_spacy_annotator():
    try:
        from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
    except ImportError as exc:
        raise EngineNotAvailable(
            "SpaCy engine requires the nlp extra. Install with: pip install datafog[nlp]"
        ) from exc

    try:
        return SpacyPIIAnnotator.create()
    except ImportError as exc:
        raise EngineNotAvailable(
            "SpaCy engine requires the nlp extra. Install with: pip install datafog[nlp]"
        ) from exc


@lru_cache(maxsize=1)
def _get_gliner_annotator():
    try:
        from .processing.text_processing.gliner_annotator import GLiNERAnnotator
    except ImportError as exc:
        raise EngineNotAvailable(
            "GLiNER engine requires the nlp-advanced extra. "
            "Install with: pip install datafog[nlp-advanced]"
        ) from exc

    try:
        annotator = GLiNERAnnotator.create()
    except ImportError as exc:
        raise EngineNotAvailable(
            "GLiNER engine requires the nlp-advanced extra. "
            "Install with: pip install datafog[nlp-advanced]"
        ) from exc

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


def _needs_ner(entity_types: Optional[list[str]]) -> bool:
    if entity_types is None:
        return True
    requested = {_canonical_type(value) for value in entity_types}
    return bool(requested & NER_ENTITY_TYPES)


def scan(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
) -> ScanResult:
    """Scan text for PII entities."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if engine not in {"regex", "spacy", "gliner", "smart"}:
        raise ValueError("engine must be one of: regex, spacy, gliner, smart")

    regex_entities = _regex_entities(text)

    if engine == "regex":
        filtered = _filter_entity_types(regex_entities, entity_types)
        return ScanResult(
            entities=_dedupe_entities(filtered), text=text, engine_used="regex"
        )

    combined: list[Entity] = list(regex_entities)
    engines_used = {"regex"}

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

    filtered = _filter_entity_types(combined, entity_types)
    deduped = _dedupe_entities(filtered)
    return ScanResult(
        entities=deduped,
        text=text,
        engine_used="+".join(sorted(engines_used)),
    )


def redact(
    text: str,
    entities: list[Entity],
    strategy: str = "token",
) -> RedactResult:
    """Redact PII entities from text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if strategy not in {"token", "mask", "hash", "pseudonymize"}:
        raise ValueError("strategy must be one of: token, mask, hash, pseudonymize")

    redacted_text = text
    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}
    pseudonym_by_value: dict[tuple[str, str], str] = {}

    valid_entities = [
        entity
        for entity in entities
        if 0 <= entity.start < entity.end <= len(text) and entity.text
    ]
    valid_entities = sorted(
        valid_entities, key=lambda e: (e.start, e.end), reverse=True
    )

    for entity in valid_entities:
        original = redacted_text[entity.start : entity.end]
        if strategy == "mask":
            replacement = "*" * max(len(original), 1)
        elif strategy == "hash":
            digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:12]
            replacement = f"[{entity.type}_{digest}]"
        elif strategy == "pseudonymize":
            key = (entity.type, original)
            if key not in pseudonym_by_value:
                counters[entity.type] = counters.get(entity.type, 0) + 1
                pseudonym_by_value[key] = (
                    f"[{entity.type}_PSEUDO_{counters[entity.type]}]"
                )
            replacement = pseudonym_by_value[key]
        else:  # token
            counters[entity.type] = counters.get(entity.type, 0) + 1
            replacement = f"[{entity.type}_{counters[entity.type]}]"

        redacted_text = (
            redacted_text[: entity.start] + replacement + redacted_text[entity.end :]
        )
        mapping[replacement] = original

    return RedactResult(
        redacted_text=redacted_text,
        mapping=mapping,
        entities=valid_entities,
    )


def scan_and_redact(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
    strategy: str = "token",
) -> RedactResult:
    """Convenience wrapper: scan then redact."""
    scan_result = scan(text=text, engine=engine, entity_types=entity_types)
    return redact(text=text, entities=scan_result.entities, strategy=strategy)
