"""Internal detection/redaction engine boundary for DataFog."""

from __future__ import annotations

import hashlib
import os
import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from .exceptions import CoreUnavailableWarning, EngineNotAvailable
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
    # Presidio-compatible aliases, so configs migrate without renames.
    "EMAIL_ADDRESS": "EMAIL",
    "US_SSN": "SSN",
    # Credential detectors are native-only; these spellings keep one vocabulary.
    "APIKEY": "API_KEY",
    "API-KEY": "API_KEY",
    "TOKEN": "BEARER_TOKEN",
    "BEARER": "BEARER_TOKEN",
    "PRIVATEKEY": "PRIVATE_KEY",
    "CREDENTIAL_URI": "CREDENTIAL_URI",
}

ALL_ENTITY_TYPES = {
    "EMAIL",
    "PHONE",
    "SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "DE_VAT_ID",
    "DE_IBAN",
    "DE_TAX_ID",
    "DE_SOCIAL_SECURITY_NUMBER",
    "DE_POSTAL_CODE",
    "DE_PASSPORT_NUMBER",
    "DE_RESIDENCE_PERMIT_NUMBER",
    "DATE",
    "ZIP_CODE",
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "ADDRESS",
    "API_KEY",
    "BEARER_TOKEN",
    "JWT",
    "PRIVATE_KEY",
    "CREDENTIAL_URI",
    "ACCOUNT_NUMBER",
    "STREET_ADDRESS",
    "US_ROUTING_NUMBER",
    "NPI",
    "UUID",
}

#: Labels the native rule engine reports as structured-only, served for text by
#: the embedded model instead.
MODEL_ENTITY_TYPES = {"PERSON", "ADDRESS"}

#: Environment override for the default backend: ``auto``, ``python`` or ``rust``.
BACKEND_ENV = "DATAFOG_BACKEND"

_core_warned = False
_cnn_cache: tuple[object, object] | None = None

NER_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS"}

ENTITY_TYPE_PRIORITY = {
    "DE_IBAN": 100,
    "DE_VAT_ID": 100,
    "DE_TAX_ID": 100,
    "DE_SOCIAL_SECURITY_NUMBER": 100,
    "DE_POSTAL_CODE": 100,
    "DE_PASSPORT_NUMBER": 100,
    "DE_RESIDENCE_PERMIT_NUMBER": 100,
    "CREDIT_CARD": 90,
    "IP_ADDRESS": 80,
    "SSN": 70,
    "PHONE": 60,
}


@dataclass(frozen=True)
class _UnavailableAnnotator:
    """Cached marker used when an optional annotator cannot be initialized."""

    message: str


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


def _entity_length(entity: Entity) -> int:
    return max(entity.end - entity.start, 0)


def _entities_overlap(left: Entity, right: Entity) -> bool:
    if left.start < 0 or right.start < 0:
        return False
    return left.start < right.end and right.start < left.end


def _suppress_overlapping_entities(entities: list[Entity]) -> list[Entity]:
    selected: list[Entity] = []
    for entity in sorted(
        entities,
        key=lambda item: (
            -_entity_length(item),
            -ENTITY_TYPE_PRIORITY.get(item.type, 0),
            -item.confidence,
            item.start,
            item.end,
            item.type,
        ),
    ):
        if any(_entities_overlap(entity, kept) for kept in selected):
            continue
        selected.append(entity)
    return sorted(selected, key=lambda item: (item.start, item.end, item.type))


def _regex_entities(
    text: str,
    entity_types: Optional[list[str]] = None,
    locales: Optional[list[str]] = None,
) -> list[Entity]:
    annotator = RegexAnnotator(locales=locales, enabled_labels=entity_types)
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
    return _suppress_overlapping_entities(entities)


def _core_module_or_none() -> object | None:
    """Return the importable ``datafog_core`` module, or ``None``.

    Deliberately uncached: after the first import this is a ``sys.modules``
    lookup, and not caching keeps ``sys.modules`` patching in tests honest.
    """
    try:
        import datafog_core
    except ImportError:
        return None
    return datafog_core


def _require_core() -> object:
    core = _core_module_or_none()
    if core is None:
        raise ImportError(
            "The Rust backend requires datafog-core. "
            'Install with: pip install "datafog[rust]"'
        )
    return core


def core_available() -> bool:
    """Whether the native engine can serve this interpreter."""
    return _core_module_or_none() is not None


def _set_core(module: object | None) -> None:
    """Test seam: reset cached state derived from the core module."""
    global _cnn_cache
    _cnn_cache = None


def _cnn_detector_or_none() -> object | None:
    """Cached embedded detector, keyed on the module object it came from."""
    global _cnn_cache
    core = _core_module_or_none()
    if core is None:
        return None
    if _cnn_cache is not None and _cnn_cache[0] is core:
        return _cnn_cache[1]
    factory = getattr(core, "EmbeddedCnnDetector", None)
    if factory is None:
        return None
    detector = factory()
    _cnn_cache = (core, detector)
    return detector


def _cnn_findings(
    detector: object, requested: set[str], text: str
) -> list[tuple[dict, object]]:
    """Serve prose names and address blocks from the embedded model."""
    try:
        result = detector.scan_model(text)
    except Exception as exc:  # relative-path/limit errors surface to the caller
        raise _model_error(exc) from exc
    return [
        ({}, finding)
        for finding in result.findings
        if finding.entity_type in requested
    ]


def _model_error(exc: Exception) -> Exception:
    """Re-raise a model failure as a ValueError with its native code attached."""
    code = getattr(exc, "code", "model_error")
    reason = getattr(exc, "reason", None)
    detail = f"{code}/{reason}" if reason else code
    error = ValueError(f"Native model detection failed ({detail}): {exc}")
    error.code = code  # type: ignore[attr-defined]
    return error


def _rust_entities(
    text: str,
    entity_types: Optional[list[str]] = None,
    locales: Optional[list[str]] = None,
) -> list[Entity]:
    """Adapt native findings to the legacy regex result contract.

    Core supplies candidate findings. Python applies the legacy overlap
    suppression before entity selection and allowlists, preserving that order
    without duplicating the native detectors.
    """
    datafog_core = _require_core()

    from ._core_capabilities import scan_configs

    requested = {_canonical_type(value) for value in entity_types or []}
    model_requested = requested & MODEL_ENTITY_TYPES
    detector = _cnn_detector_or_none() if model_requested else None
    if model_requested and detector is None:
        raise ValueError(
            f"Entity {', '.join(sorted(model_requested))} needs the embedded model, "
            "which this datafog-core build does not provide. Upgrade it with: "
            'pip install --upgrade "datafog-core"'
        )
    configs = scan_configs(datafog_core, requested - MODEL_ENTITY_TYPES, locales)
    entities: list[Entity] = []
    seen: set[tuple[str, int, int]] = set()
    findings = [
        (config, finding)
        for config in configs
        for finding in datafog_core.scan(text, config=config)
    ]
    if detector is not None:
        findings.extend(_cnn_findings(detector, model_requested, text))
    for config, finding in findings:
            canonical_type = _canonical_type(finding.entity_type)
            start = finding.codepoint_range.start
            end = finding.codepoint_range.end
            key = (canonical_type, start, end)
            if key in seen or not finding.matched_text.strip():
                continue
            seen.add(key)
            entities.append(
                Entity(
                    type=canonical_type,
                    text=finding.matched_text,
                    start=start,
                    end=end,
                    confidence=1.0,
                    engine="regex",
                )
            )
    return _suppress_overlapping_entities(entities)


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


# Python's re module backtracks; a quantified group containing another
# quantifier (e.g. ``(a+)+``) can take exponential time on adversarial
# input, and entity text can be attacker-influenced (LLM messages, tool
# output). Reject that construct outright rather than matching under it.
_NESTED_QUANTIFIER = re.compile(
    r"\((?:[^()\\]|\\.)*(?<!\\)[+*}](?:[^()\\]|\\.)*\)\s*[+*{]"
)
MAX_ALLOWLIST_PATTERN_LENGTH = 512
# Entities longer than this skip pattern matching (fail-safe: the finding
# is kept, never suppressed) so match time stays bounded.
MAX_PATTERN_SUBJECT_LENGTH = 512


def _compile_allowlist_patterns(
    allowlist_patterns: Optional[list[str]],
) -> list["re.Pattern[str]"]:
    compiled = []
    for raw in allowlist_patterns or []:
        if len(raw) > MAX_ALLOWLIST_PATTERN_LENGTH:
            raise ValueError(
                "allowlist_patterns entries must be at most "
                f"{MAX_ALLOWLIST_PATTERN_LENGTH} characters"
            )
        if _NESTED_QUANTIFIER.search(raw):
            raise ValueError(
                "allowlist_patterns contains a quantified group with a nested "
                f"quantifier ({raw!r}), which risks catastrophic backtracking; "
                "rewrite the pattern without nesting quantifiers"
            )
        try:
            compiled.append(re.compile(raw))
        except re.error as exc:
            raise ValueError(
                f"allowlist_patterns contains an invalid regex: {raw!r} ({exc})"
            ) from None
    return compiled


def _apply_allowlist(
    entities: list[Entity],
    allowlist: Optional[list[str]],
    allowlist_patterns: Optional[list[str]],
) -> list[Entity]:
    """Drop entities whose exact text is allowlisted.

    Matching semantics, deliberately strict for a security boundary:
    exact values are case-sensitive with no Unicode normalization, and
    patterns must fullmatch the entity text, so a partial match never
    suppresses a finding. Allowlist entries and patterns are operator
    configuration; treat them like code and never accept them from end
    users.
    """
    if not allowlist and not allowlist_patterns:
        return entities
    exact = set(allowlist or [])
    patterns = _compile_allowlist_patterns(allowlist_patterns)
    return [
        entity
        for entity in entities
        if entity.text not in exact
        and not any(
            pattern.fullmatch(entity.text)
            for pattern in patterns
            if len(entity.text) <= MAX_PATTERN_SUBJECT_LENGTH
        )
    ]


def _needs_ner(entity_types: Optional[list[str]]) -> bool:
    if entity_types is None:
        return True
    requested = {_canonical_type(value) for value in entity_types}
    return bool(requested & NER_ENTITY_TYPES)


def _warn_core_missing() -> None:
    global _core_warned
    if _core_warned:
        return
    _core_warned = True
    warnings.warn(
        "datafog-core is not installed, so detection falls back to the pure-Python "
        f"engine. Install it to use the native engine, or set {BACKEND_ENV}=python "
        "to silence this warning.",
        CoreUnavailableWarning,
        stacklevel=4,
    )


def resolve_backend(backend: str | None = None, engine: str = "regex") -> str:
    """Resolve ``auto`` to a concrete backend without importing Core eagerly.

    An explicit ``backend`` wins over ``DATAFOG_BACKEND``. ``auto`` uses the
    native engine whenever Core is importable and degrades to Python otherwise.
    Non-``regex`` engines always take the Python path, because the native
    backend serves ``regex`` and model findings only.
    """
    requested = backend or os.environ.get(BACKEND_ENV) or "auto"
    normalized = requested.strip().lower()
    if normalized not in {"auto", "python", "rust"}:
        raise ValueError(
            f"backend must be one of: auto, python, rust (from {BACKEND_ENV} or the "
            "backend argument)"
        )
    if normalized == "auto":
        if engine != "regex":
            return "python"
        return "rust" if core_available() else "python"
    return normalized


def _validate_backend(backend: str, engine: str) -> None:
    if backend not in {"python", "rust"}:
        raise ValueError("backend must be one of: python, rust")
    if backend == "rust" and engine != "regex":
        raise ValueError("backend='rust' supports only engine='regex'")


def scan(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
    locales: Optional[list[str]] = None,
    allowlist: Optional[list[str]] = None,
    allowlist_patterns: Optional[list[str]] = None,
    *,
    backend: Optional[str] = None,
) -> ScanResult:
    """Scan text for PII entities.

    ``backend`` defaults to ``auto``: the native engine when ``datafog-core`` is
    importable, otherwise the pure-Python engine with a one-time warning. Set
    ``DATAFOG_BACKEND`` or pass ``backend="python"`` to force the fallback. The
    native path serves ``engine="regex"``; non-regex engines always use Python.
    Probe names and address blocks come from the embedded model on the native
    path, so ``PERSON`` and ``ADDRESS`` work without spaCy or a model download.

    Results retain legacy regex provenance and confidence; these are
    compatibility values, not native confidence estimates.

    ``allowlist`` exempts exact entity texts (e.g. your own support email);
    ``allowlist_patterns`` exempts entities whose full text matches a regex
    (e.g. ``^\\d{10}$`` to stop unix timestamps matching as phone numbers).
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if engine not in {"regex", "spacy", "gliner", "smart"}:
        raise ValueError("engine must be one of: regex, spacy, gliner, smart")

    requested_backend = (backend or os.environ.get(BACKEND_ENV) or "auto").strip().lower()
    backend = resolve_backend(backend, engine)
    _validate_backend(backend, engine)
    if backend == "python" and requested_backend == "auto" and not core_available():
        _warn_core_missing()

    # Validate patterns up front so config errors fail fast even when the
    # text contains no entities.
    _compile_allowlist_patterns(allowlist_patterns)

    detector = _rust_entities if backend == "rust" else _regex_entities
    regex_entities = detector(
        text,
        entity_types=entity_types,
        locales=locales,
    )

    if engine == "regex":
        filtered = _filter_entity_types(regex_entities, entity_types)
        filtered = _apply_allowlist(filtered, allowlist, allowlist_patterns)
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
    filtered = _apply_allowlist(filtered, allowlist, allowlist_patterns)
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
    """Redact PII entities from text.

    Callers may pass arbitrary entity lists (not just ``scan()`` output), so
    overlapping or duplicate spans are resolved here: for each overlapping
    group only one span is redacted — the longest, breaking ties by entity
    type priority and then confidence. Suppressed spans are omitted from
    ``RedactResult.entities`` and ``mapping``.

    ``mapping`` for the ``mask`` strategy is keyed by per-type indexed keys
    (``[EMAIL_MASK_1]``) rather than the mask string, because distinct
    same-length values produce identical masks and would collide.
    """
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
    # Returns non-overlapping spans sorted by document position.
    valid_entities = _suppress_overlapping_entities(valid_entities)

    # Assign replacements in document order so the per-type counters used by
    # the token/pseudonymize strategies number the first occurrence _1; spans
    # are applied right-to-left below so earlier offsets stay valid.
    replacements: list[tuple[Entity, str]] = []
    for entity in valid_entities:
        original = text[entity.start : entity.end]
        mapping_key: Optional[str] = None
        if strategy == "mask":
            replacement = "*" * max(len(original), 1)
            # Distinct same-length values share a mask, so the mask string
            # cannot key the mapping without collisions.
            counters[entity.type] = counters.get(entity.type, 0) + 1
            mapping_key = f"[{entity.type}_MASK_{counters[entity.type]}]"
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

        replacements.append((entity, replacement))
        mapping[mapping_key if mapping_key is not None else replacement] = original

    for entity, replacement in reversed(replacements):
        redacted_text = (
            redacted_text[: entity.start] + replacement + redacted_text[entity.end :]
        )

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
    locales: Optional[list[str]] = None,
    allowlist: Optional[list[str]] = None,
    allowlist_patterns: Optional[list[str]] = None,
    *,
    backend: Optional[str] = None,
) -> RedactResult:
    """Scan with the selected backend, then apply legacy Python redaction.

    Backend selection matches :func:`scan`.
    """
    scan_result = scan(
        text=text,
        engine=engine,
        entity_types=entity_types,
        locales=locales,
        allowlist=allowlist,
        allowlist_patterns=allowlist_patterns,
        backend=backend,
    )
    return redact(text=text, entities=scan_result.entities, strategy=strategy)
