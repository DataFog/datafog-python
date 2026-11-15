"""Internal detection/redaction engine boundary for DataFog."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import regex as bounded_re

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
    "PASSPORT_NUMBER",
    "MEDICAL_RECORD_NUMBER",
    "LICENSE_NUMBER",
    "URL",
}

#: Labels the native rule engine reports as structured-only, served for text by
#: the embedded model instead.
MODEL_ENTITY_TYPES = {"PERSON", "ADDRESS"}

#: Environment override for the default backend: ``auto``, ``python`` or ``rust``.
BACKEND_ENV = "DATAFOG_BACKEND"

_core_warned = False
_cnn_cache: tuple[object, object] | None = None

NER_ENTITY_TYPES = {
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "ADDRESS",
    "PASSPORT_NUMBER",
    "MEDICAL_RECORD_NUMBER",
    "LICENSE_NUMBER",
    "URL",
}

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
    """Compatibility for third-party annotators without offset support.

    Whole-word matching avoids interpreting "Ann" inside "Annual" as a name.
    First-party annotators use their original character ranges instead.
    """
    entities: list[Entity] = []
    value_offsets: dict[str, int] = {}
    for raw_type, values in payload.items():
        canonical_type = _canonical_type(raw_type)
        if canonical_type not in ALL_ENTITY_TYPES:
            continue
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            pattern = re.compile(r"(?<!\w)" + re.escape(value) + r"(?!\w)")
            match = pattern.search(text, value_offsets.get(value, 0))
            if match is None:
                continue
            value_offsets[value] = match.end()
            entities.append(
                Entity(
                    canonical_type,
                    value,
                    match.start(),
                    match.end(),
                    confidence,
                    engine,
                )
            )
    return entities


def _annotator_entities(
    text: str, annotator: object, engine: str, confidence: float
) -> list[Entity]:
    method = getattr(annotator, "annotate_with_spans", None)
    if not callable(method):
        return _entities_from_dict(text, annotator.annotate(text), engine, confidence)
    _, result = method(text)
    entities = []
    for span in result.spans:
        label = _canonical_type(span.label)
        if label not in ALL_ENTITY_TYPES:
            continue
        if (
            not 0 <= span.start < span.end <= len(text)
            or text[span.start : span.end] != span.text
        ):
            raise ValueError(f"{engine} returned an invalid entity span")
        entities.append(
            Entity(label, span.text, span.start, span.end, confidence, engine)
        )
    return entities


def _entity_length(entity: Entity) -> int:
    return max(entity.end - entity.start, 0)


def _entities_overlap(left: Entity, right: Entity) -> bool:
    if left.start < 0 or right.start < 0:
        return False
    return left.start < right.end and right.start < left.end


def _suppress_overlapping_entities(entities: list[Entity]) -> list[Entity]:
    """Preserve longest-span precedence with O(n log n) interval queries."""
    coordinates = {
        value: index + 1
        for index, value in enumerate(
            sorted(
                {value for entity in entities for value in (entity.start, entity.end)}
            )
        )
    }
    starts = [0] * (len(coordinates) + 1)
    ends = [0] * (len(coordinates) + 1)

    def add(tree: list[int], index: int) -> None:
        while index < len(tree):
            tree[index] += 1
            index += index & -index

    def count(tree: list[int], index: int) -> int:
        total = 0
        while index > 0:
            total += tree[index]
            index -= index & -index
        return total

    selected = []
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
        start, end = coordinates[entity.start], coordinates[entity.end]
        if count(starts, end - 1) > count(ends, start):
            continue
        selected.append(entity)
        add(starts, start)
        add(ends, end)
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
) -> list[tuple[int, object]]:
    """Bound model work while retaining document character coordinates.

    4096 characters fit the native byte/token caps even for four-byte Unicode.
    Overlap gives names and address blocks context on either side of a seam.
    """
    chunk_length, overlap = 4096, 256
    findings = []
    for offset in range(0, max(len(text), 1), chunk_length - overlap):
        chunk = text[offset : offset + chunk_length]
        try:
            result = detector.scan_model(chunk)
        except Exception as exc:
            raise _model_error(exc) from exc
        findings.extend(
            (offset, finding)
            for finding in result.findings
            if finding.entity_type in requested
        )
        if offset + chunk_length >= len(text):
            break
    return findings


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
    native_text = re.sub(r"[\ud800-\udfff]", "\ufffd", text)
    findings = [
        (0, finding)
        for config in configs
        for finding in datafog_core.scan(native_text, config=config)
    ]
    if detector is not None:
        findings.extend(_cnn_findings(detector, model_requested, native_text))
    for offset, finding in findings:
        canonical_type = _canonical_type(finding.entity_type)
        start = offset + finding.codepoint_range.start
        end = offset + finding.codepoint_range.end
        key = (canonical_type, start, end)
        if key in seen or not finding.matched_text.strip():
            continue
        seen.add(key)
        entities.append(
            Entity(
                type=canonical_type,
                text=text[start:end],
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
    return [
        entity
        for entity in _annotator_entities(text, annotator, "spacy", 0.7)
        if entity.type in NER_ENTITY_TYPES
    ]


def _gliner_entities(text: str, model_name: str | None = None) -> list[Entity]:
    annotator = (
        _get_gliner_annotator()
        if model_name is None
        else _get_gliner_annotator(model_name)
    )
    if isinstance(annotator, _UnavailableAnnotator):
        raise EngineNotAvailable(annotator.message)
    return _annotator_entities(text, annotator, "gliner", 0.8)


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


@lru_cache(maxsize=4)
def _get_gliner_annotator(model_name: str = "urchade/gliner_multi_pii-v1"):
    try:
        from .processing.text_processing.gliner_annotator import GLiNERAnnotator
    except ImportError as exc:
        return _UnavailableAnnotator(str(exc))

    try:
        annotator = GLiNERAnnotator.create(model_name=model_name)
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


MAX_ALLOWLIST_PATTERN_LENGTH = 512
MAX_PATTERN_SUBJECT_LENGTH = 512
ALLOWLIST_MATCH_TIMEOUT = 0.01


def _compile_allowlist_patterns(allowlist_patterns: Optional[list[str]]) -> list:
    compiled = []
    if isinstance(allowlist_patterns, str):
        raise ValueError("allowlist_patterns must be a list of patterns")
    for raw in allowlist_patterns or []:
        if not isinstance(raw, str) or len(raw) > MAX_ALLOWLIST_PATTERN_LENGTH:
            raise ValueError(
                "allowlist_patterns entries must be strings of at most 512 characters"
            )
        try:
            compiled.append(bounded_re.compile(raw))
        except bounded_re.error as exc:
            raise ValueError(
                f"allowlist_patterns contains an invalid regex: {raw!r} ({exc})"
            ) from None
    return compiled


def _allowlist_matches(pattern: object, value: str) -> bool:
    if len(value) > MAX_PATTERN_SUBJECT_LENGTH:
        return False
    try:
        return pattern.fullmatch(value, timeout=ALLOWLIST_MATCH_TIMEOUT) is not None
    except TimeoutError:
        # A slow exemption must never suppress a sensitive finding.
        return False


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
        and not any(_allowlist_matches(pattern, entity.text) for pattern in patterns)
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
    Every engine uses this backend for structured PII; NER adds spans.
    """
    requested = backend or os.environ.get(BACKEND_ENV) or "auto"
    normalized = requested.strip().lower()
    if normalized not in {"auto", "python", "rust"}:
        raise ValueError(
            f"backend must be one of: auto, python, rust (from {BACKEND_ENV} or the "
            "backend argument)"
        )
    if normalized == "auto":
        return "rust" if core_available() else "python"
    return normalized


def _validate_backend(backend: str, engine: str) -> None:
    if backend not in {"python", "rust"}:
        raise ValueError("backend must be one of: python, rust")


def _validate_entity_types(
    entity_types: Optional[list[str]], backend: str, engine: str
) -> Optional[list[str]]:
    if entity_types is None:
        return None
    if not isinstance(entity_types, (list, tuple)) or any(
        not isinstance(value, str) or not value.strip() for value in entity_types
    ):
        raise ValueError("entity_types must be a list of entity labels")
    requested = [_canonical_type(value) for value in entity_types]
    if backend == "rust":
        from ._core_capabilities import _read_capabilities

        supported, _, _ = _read_capabilities(_require_core().capabilities)
        supported = supported | MODEL_ENTITY_TYPES
    else:
        supported = {_canonical_type(label) for label in RegexAnnotator.LABELS}
    if engine != "regex":
        supported |= NER_ENTITY_TYPES | {"DATE"}
    unsupported = set(requested) - supported
    if unsupported:
        raise ValueError(
            f"Unsupported entity_types for {backend}/{engine}: {', '.join(sorted(unsupported))}"
        )
    return requested


def scan(
    text: str,
    engine: str = "smart",
    entity_types: Optional[list[str]] = None,
    locales: Optional[list[str]] = None,
    allowlist: Optional[list[str]] = None,
    allowlist_patterns: Optional[list[str]] = None,
    *,
    backend: Optional[str] = None,
    gliner_model: Optional[str] = None,
) -> ScanResult:
    """Scan text for PII entities.

    ``backend`` defaults to ``auto``: the native engine when ``datafog-core`` is
    importable, otherwise the pure-Python engine with a one-time warning. Set
    ``DATAFOG_BACKEND`` or pass ``backend="python"`` to force the fallback. The
    selected backend supplies structured PII for every engine mode; optional
    NER engines add entity spans.
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

    requested_backend = (
        (backend or os.environ.get(BACKEND_ENV) or "auto").strip().lower()
    )
    backend = resolve_backend(backend, engine)
    _validate_backend(backend, engine)
    entity_types = _validate_entity_types(entity_types, backend, engine)
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
            gliner_entities = (
                _gliner_entities(text)
                if gliner_model is None
                else _gliner_entities(text, gliner_model)
            )
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
            gliner_entities = (
                _gliner_entities(text)
                if gliner_model is None
                else _gliner_entities(text, gliner_model)
            )
            combined.extend(gliner_entities)
            engines_used.add("gliner")
        except EngineNotAvailable as exc:
            warnings.warn(
                f"GLiNER unavailable; smart scan falling back to spaCy. {exc}",
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
    deduped = _suppress_overlapping_entities(_dedupe_entities(filtered))
    return ScanResult(
        entities=deduped,
        text=text,
        engine_used="+".join(sorted(engines_used)),
    )


def _validate_hash_parameters(
    strategy: str, hash_type: str, hash_key: bytes | None
) -> None:
    if hash_key is not None and (not isinstance(hash_key, bytes) or len(hash_key) < 32):
        raise ValueError("hash_key must contain at least 32 bytes")
    if strategy == "hash":
        try:
            hashlib.new(hash_type).hexdigest()
        except (ValueError, TypeError):
            raise ValueError(f"Unsupported hash_type: {hash_type!r}") from None


def _validated_redaction_entities(text: str, entities: list[Entity]) -> list[Entity]:
    valid_entities = []
    for entity in entities:
        if (
            not 0 <= entity.start < entity.end <= len(text)
            or not entity.text
            or text[entity.start : entity.end] != entity.text
        ):
            raise ValueError(
                "entities must contain valid ranges whose text matches the source"
            )
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", entity.type):
            raise ValueError("entity types must be uppercase labels")
        valid_entities.append(entity)
    return _suppress_overlapping_entities(valid_entities)


def redact(
    text: str,
    entities: list[Entity],
    strategy: str = "token",
    *,
    hash_type: str = "sha256",
    hash_key: bytes | None = None,
) -> RedactResult:
    """Redact PII entities from text.

    Callers may pass arbitrary entity lists (not just ``scan()`` output), so
    overlapping or duplicate spans are resolved here: for each overlapping
    group only one span is redacted — the longest, breaking ties by entity
    type priority and then confidence. Suppressed spans are omitted from
    ``RedactResult.entities`` and ``mapping``.

    Invalid ranges, mismatched source text, and malformed labels raise ValueError.

    ``mapping`` for the ``mask`` strategy is keyed by per-type indexed keys
    (``[EMAIL_MASK_1]``) rather than the mask string, because distinct
    same-length values produce identical masks and would collide.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if strategy not in {"token", "mask", "hash", "pseudonymize"}:
        raise ValueError("strategy must be one of: token, mask, hash, pseudonymize")

    _validate_hash_parameters(strategy, hash_type, hash_key)

    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}
    pseudonym_by_value: dict[tuple[str, str], str] = {}

    valid_entities = _validated_redaction_entities(text, entities)

    occupied_tokens = set(re.findall(r"\[[A-Z][A-Za-z0-9_]*\]", text))

    # Assign replacements in document order so the per-type counters used by
    # the token/pseudonymize strategies number the first occurrence _1.
    # Assemble the result in one pass without repeated document copies.
    replacements: list[tuple[Entity, str]] = []
    for entity in valid_entities:
        original = text[entity.start : entity.end]
        mapping_key: Optional[str] = None
        if strategy == "mask":
            replacement = "*" * max(len(original), 1)
            # Distinct same-length values share a mask, so the mask string
            # cannot key the mapping without collisions.
            while True:
                counters[entity.type] = counters.get(entity.type, 0) + 1
                mapping_key = f"[{entity.type}_MASK_{counters[entity.type]}]"
                if mapping_key not in occupied_tokens:
                    break
            occupied_tokens.add(mapping_key)
        elif strategy == "hash":
            encoded = original.encode("utf-8", "surrogatepass")
            digest = (
                hmac.new(hash_key, encoded, hash_type).hexdigest()
                if hash_key is not None
                else hashlib.new(hash_type, encoded).hexdigest()
            )
            key = (entity.type, original)
            if key not in pseudonym_by_value:
                candidate = f"[{entity.type}_{digest}]"
                suffix = 1
                while candidate in occupied_tokens:
                    suffix += 1
                    candidate = f"[{entity.type}_{digest}_{suffix}]"
                pseudonym_by_value[key] = candidate
                occupied_tokens.add(candidate)
            replacement = pseudonym_by_value[key]
        elif strategy == "pseudonymize":
            key = (entity.type, original)
            if key not in pseudonym_by_value:
                while True:
                    counters[entity.type] = counters.get(entity.type, 0) + 1
                    candidate = f"[{entity.type}_PSEUDO_{counters[entity.type]}]"
                    if candidate not in occupied_tokens:
                        break
                pseudonym_by_value[key] = candidate
                occupied_tokens.add(candidate)
            replacement = pseudonym_by_value[key]
        else:  # token
            key = (entity.type, original)
            if key not in pseudonym_by_value:
                while True:
                    counters[entity.type] = counters.get(entity.type, 0) + 1
                    candidate = f"[{entity.type}_{counters[entity.type]}]"
                    if candidate not in occupied_tokens:
                        break
                pseudonym_by_value[key] = candidate
                occupied_tokens.add(candidate)
            replacement = pseudonym_by_value[key]

        replacements.append((entity, replacement))
        mapping[mapping_key if mapping_key is not None else replacement] = original

    parts = []
    offset = 0
    for entity, replacement in replacements:
        parts.extend((text[offset : entity.start], replacement))
        offset = entity.end
    parts.append(text[offset:])
    redacted_text = "".join(parts)

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
    hash_type: str = "sha256",
    hash_key: bytes | None = None,
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
    return redact(
        text=text,
        entities=scan_result.entities,
        strategy=strategy,
        hash_type=hash_type,
        hash_key=hash_key,
    )
