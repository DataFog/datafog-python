"""
DataFog: Lightning-fast PII detection and anonymization library.

Core package provides regex-based PII detection, 100x+ faster than NER-based
detection on identical payloads (reproduce: python benchmarks/run.py).
Optional extras available for advanced features:
- pip install datafog[nlp] - for spaCy integration
- pip install datafog[ocr] - for image/OCR processing
- pip install datafog[all] - for all features
"""

import warnings

from .__about__ import __version__
from ._legacy_retirement import LAST_SUPPORTED as _LAST_SUPPORTED
from .agent import create_guardrail, filter_output, sanitize, scan_prompt

# Core API functions - always available (lightweight)
from .compat import v4 as _compat_v4
from .core import anonymize_text, detect_pii, get_supported_entities, scan_text
from .engine import Entity, RedactResult, ScanResult

# Essential models - always available
from .models.common import EntityTypes


# Conditional imports for better lightweight performance
def _lazy_import_core_models():
    """Lazy import of core models to reduce startup time."""
    global AnnotationResult, AnnotatorRequest, AnonymizationResult
    global Anonymizer, AnonymizerRequest, AnonymizerType

    if "AnnotationResult" not in globals():
        from .models.annotator import AnnotationResult, AnnotatorRequest
        from .models.anonymizer import (
            AnonymizationResult,
            Anonymizer,
            AnonymizerRequest,
            AnonymizerType,
        )

        globals().update(
            {
                "AnnotationResult": AnnotationResult,
                "AnnotatorRequest": AnnotatorRequest,
                "AnonymizationResult": AnonymizationResult,
                "Anonymizer": Anonymizer,
                "AnonymizerRequest": AnonymizerRequest,
                "AnonymizerType": AnonymizerType,
            }
        )


def _lazy_import_regex_annotator():
    """Lazy import of regex annotator to reduce startup time."""
    global RegexAnnotator

    if "RegexAnnotator" not in globals():
        from .processing.text_processing.regex_annotator import RegexAnnotator

        globals()["RegexAnnotator"] = RegexAnnotator


def __getattr__(name: str):
    """Handle lazy imports for better lightweight performance."""
    # Lazy import core models when first accessed
    if name in {
        "AnnotationResult",
        "AnnotatorRequest",
        "AnonymizationResult",
        "Anonymizer",
        "AnonymizerRequest",
        "AnonymizerType",
    }:
        _lazy_import_core_models()
        return globals()[name]

    # Lazy import regex annotator when first accessed
    elif name == "RegexAnnotator":
        _lazy_import_regex_annotator()
        return globals()[name]

    elif name in _LAZY_EXPORTS:
        module_path, attr_name, extra_name = _LAZY_EXPORTS[name]
        if attr_name is None:
            # Submodule export (``datafog.native``): return the module itself.
            import importlib

            value = importlib.import_module(module_path)
            globals()[name] = value
            return value
        try:
            module = __import__(module_path, fromlist=[attr_name])
            value = getattr(module, attr_name)
        except ImportError:
            if extra_name is None:
                value = None
            else:

                def _missing_dependency(*args, **kwargs):
                    raise ImportError(
                        f"{name} requires additional dependencies. "
                        f"Install with: pip install datafog[{extra_name}]"
                    )

                value = _missing_dependency

        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_LAZY_EXPORTS = {
    "native": ("datafog.native", None, None),
    "app": ("datafog.client", "app", None),
    "DataFog": ("datafog.main", "DataFog", None),
    "TextPIIAnnotator": ("datafog.main", "TextPIIAnnotator", None),
    "TextService": ("datafog.services.text_service", "TextService", None),
    "DonutProcessor": (
        "datafog.processing.image_processing.donut_processor",
        "DonutProcessor",
        "ocr",
    ),
    "PytesseractProcessor": (
        "datafog.processing.image_processing.pytesseract_processor",
        "PytesseractProcessor",
        "ocr",
    ),
    "ImageService": ("datafog.services.image_service", "ImageService", "ocr"),
    "SpacyPIIAnnotator": (
        "datafog.processing.text_processing.spacy_pii_annotator",
        "SpacyPIIAnnotator",
        "nlp",
    ),
    "SparkService": ("datafog.services.spark_service", "SparkService", "distributed"),
}


def _warn_v5_replacement(old_api: str, replacement: str) -> None:
    warnings.warn(
        f"datafog.{old_api}() is deprecated and will be removed in 5.0. Use {replacement} instead. "
        f'Last supported version is {_LAST_SUPPORTED}. Pin it with: pip install "datafog=={_LAST_SUPPORTED}". '
        "The earlier promise to retain this shim through 5.x has been revised. See docs/retirement.rst.",
        FutureWarning,
        stacklevel=3,
    )


def scan(
    text: str,
    engine: str = "regex",
    entity_types: list[str] | None = None,
    locales: list[str] | None = None,
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
    *,
    backend: str | None = None,
) -> ScanResult:
    """Scan using the 4.x compatibility API; native detection is the default."""
    return _compat_v4.scan(
        text,
        engine,
        entity_types,
        locales,
        allowlist,
        allowlist_patterns,
        backend=backend,
    )


def redact(
    text: str,
    entities: list[Entity] | None = None,
    engine: str = "regex",
    entity_types: list[str] | None = None,
    strategy: str = "token",
    preset: str | None = None,
    locales: list[str] | None = None,
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
    *,
    backend: str | None = None,
    hash_type: str = "sha256",
    hash_key: bytes | None = None,
) -> RedactResult:
    """Redact using the 4.x compatibility API and legacy strategies."""
    return _compat_v4.redact(
        text,
        entities,
        engine,
        entity_types,
        strategy,
        preset,
        locales,
        allowlist,
        allowlist_patterns,
        backend=backend,
        hash_type=hash_type,
        hash_key=hash_key,
    )


def protect(
    entity_types: list[str] | None = None,
    engine: str = "regex",
    strategy: str = "token",
    on_detect: str = "redact",
    locales: list[str] | None = None,
):
    """
    v5-preview guardrail factory.
    """
    return create_guardrail(
        entity_types=entity_types,
        engine=engine,
        strategy=strategy,
        on_detect=on_detect,
        locales=locales,
    )


# Simple API for core functionality (backward compatibility)
def detect(text: str) -> list:
    """
    Detect PII in text using regex patterns.

    Args:
        text: Input text to scan for PII

    Returns:
        List of detected PII entities

    Example:
        >>> from datafog import detect
        >>> detect("Contact john@example.com")
        [{'type': 'EMAIL', 'value': 'john@example.com', 'start': 8, 'end': 24}]
    """
    _warn_v5_replacement("detect", "datafog.scan()")

    return _detect_impl(text)


def _detect_impl(text: str) -> list:
    import time as _time

    _start = _time.monotonic()

    result = scan(text)

    # Convert to simple format, filtering out empty matches
    entities = []
    for span in result.entities:
        if span.text.strip():  # Only include non-empty matches
            entities.append(
                {
                    "type": span.type,
                    "value": span.text,
                    "start": span.start,
                    "end": span.end,
                }
            )

    try:
        from .telemetry import (
            _get_duration_bucket,
            _get_text_length_bucket,
            track_function_call,
        )

        _duration = (_time.monotonic() - _start) * 1000
        entity_types = list({e["type"] for e in entities})
        track_function_call(
            function_name="detect",
            module="datafog",
            engine="regex",
            text_length_bucket=_get_text_length_bucket(len(text)),
            entity_count=len(entities),
            entity_types_found=entity_types,
            duration_ms_bucket=_get_duration_bucket(_duration),
        )
    except Exception:
        pass

    return entities


def process(
    text: str,
    anonymize: bool = False,
    method: str = "redact",
    *,
    hash_type: str | None = None,
    hash_key: bytes | None = None,
) -> dict:
    """
    Process text to detect and optionally anonymize PII.

    Args:
        text: Input text to process
        anonymize: Whether to anonymize detected PII
        method: Anonymization method ('redact', 'replace', 'hash')
        hash_type: Optional algorithm. The legacy plain-hash default is MD5;
            keyed hashes default to SHA256.
        hash_key: At least 32 bytes for a full keyed HMAC digest.

    Returns:
        Dictionary with original text, anonymized text (if requested), and findings

    Example:
        >>> from datafog import process
        >>> process("Contact john@example.com", anonymize=True)
        {
            'original': 'Contact john@example.com',
            'anonymized': 'Contact [EMAIL_REDACTED]',
            'findings': [{'type': 'EMAIL', 'value': 'john@example.com', ...}]
        }
    """
    _warn_v5_replacement("process", "datafog.scan() or datafog.redact()")

    import time as _time

    _start = _time.monotonic()

    if method not in {"redact", "replace", "hash"}:
        raise ValueError("method must be 'redact', 'replace', or 'hash'")
    if anonymize and method == "hash":
        from .engine import _hash_value, _validate_hash_parameters

        algorithm = (
            hash_type
            if hash_type is not None
            else ("sha256" if hash_key is not None else "md5")
        )
        _validate_hash_parameters("hash", algorithm, hash_key)
    findings = _detect_impl(text)

    result = {"original": text, "findings": findings}

    if anonymize:
        parts = []
        cursor = 0
        suffix = "REDACTED" if method == "redact" else "XXXXX"
        for finding in sorted(findings, key=lambda item: item["start"]):
            if method == "hash":
                digest = _hash_value(
                    finding["value"], algorithm, hash_key, plain_length=8
                )
                replacement = f"[{finding['type']}_{digest}]"
            else:
                replacement = f"[{finding['type']}_{suffix}]"
            parts.extend((text[cursor : finding["start"]], replacement))
            cursor = finding["end"]
        parts.append(text[cursor:])
        result["anonymized"] = "".join(parts)

    try:
        from .telemetry import _get_duration_bucket, track_function_call

        _duration = (_time.monotonic() - _start) * 1000
        track_function_call(
            function_name="process",
            module="datafog",
            anonymize=anonymize,
            method=method,
            entity_count=len(findings),
            duration_ms_bucket=_get_duration_bucket(_duration),
        )
    except Exception:
        pass

    return result


# Core exports
__all__ = [
    "__version__",
    "Entity",
    "ScanResult",
    "RedactResult",
    "scan",
    "redact",
    "protect",
    "detect",
    "process",
    "detect_pii",
    "anonymize_text",
    "scan_text",
    "get_supported_entities",
    "sanitize",
    "scan_prompt",
    "filter_output",
    "create_guardrail",
    "AnnotationResult",
    "AnnotatorRequest",
    "AnonymizationResult",
    "Anonymizer",
    "AnonymizerRequest",
    "AnonymizerType",
    "EntityTypes",
    "RegexAnnotator",
    # Optional exports (may be None if dependencies missing)
    "DataFog",
    "TextPIIAnnotator",
    "TextService",
    "app",
    "DonutProcessor",
    "PytesseractProcessor",
    "ImageService",
    "SpacyPIIAnnotator",
    "SparkService",
]
