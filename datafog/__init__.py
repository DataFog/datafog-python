"""
DataFog: Lightning-fast PII detection and anonymization library.

Core package provides regex-based PII detection with 190x performance advantage.
Optional extras available for advanced features:
- pip install datafog[nlp] - for spaCy integration
- pip install datafog[ocr] - for image/OCR processing
- pip install datafog[all] - for all features
"""

import warnings

from .__about__ import __version__
from .agent import create_guardrail, filter_output, sanitize, scan_prompt
from .engine import (
    Entity,
    RedactResult,
    ScanResult,
    redact as _redact_entities,
    scan as _scan,
    scan_and_redact as _scan_and_redact,
)

# Core API functions - always available (lightweight)
from .core import anonymize_text, detect_pii, get_supported_entities, scan_text

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


# Optional imports with graceful fallback
try:
    from .client import app
except ImportError:
    app = None

try:
    from .main import DataFog, TextPIIAnnotator
except ImportError:
    DataFog = None
    TextPIIAnnotator = None

try:
    from .services.text_service import TextService
except ImportError:
    TextService = None


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

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Optional heavy features - only import if dependencies available
def _optional_import(name, module_path, extra_name):
    """Helper to import optional modules with helpful error messages."""
    try:
        module = __import__(module_path, fromlist=[name])
        return getattr(module, name)
    except ImportError:

        def _missing_dependency(*args, **kwargs):
            raise ImportError(
                f"{name} requires additional dependencies. "
                f"Install with: pip install datafog[{extra_name}]"
            )

        return _missing_dependency


# OCR/Image processing - requires 'ocr' extra
DonutProcessor = _optional_import(
    "DonutProcessor", "datafog.processing.image_processing.donut_processor", "ocr"
)
PytesseractProcessor = _optional_import(
    "PytesseractProcessor",
    "datafog.processing.image_processing.pytesseract_processor",
    "ocr",
)
ImageService = _optional_import("ImageService", "datafog.services.image_service", "ocr")

# NLP processing - requires 'nlp' extra
SpacyPIIAnnotator = _optional_import(
    "SpacyPIIAnnotator", "datafog.processing.text_processing.spacy_pii_annotator", "nlp"
)

# Distributed processing - requires 'distributed' extra
SparkService = _optional_import(
    "SparkService", "datafog.services.spark_service", "distributed"
)


_REDACT_PRESETS = {
    "default": "token",
    "llm": "token",
    "mask": "mask",
    "hash": "hash",
    "replace": "pseudonymize",
    "pseudonymize": "pseudonymize",
}


def _warn_v5_replacement(old_api: str, replacement: str) -> None:
    warnings.warn(
        f"datafog.{old_api}() is deprecated for v5. Use {replacement} instead. "
        "This compatibility shim will remain through the v5.x line.",
        FutureWarning,
        stacklevel=3,
    )


def scan(
    text: str,
    engine: str = "regex",
    entity_types: list[str] | None = None,
) -> ScanResult:
    """
    v5-preview scan entrypoint.

    Defaults to the lightweight regex engine so the core install works without
    optional dependency fallback warnings.
    """
    return _scan(text=text, engine=engine, entity_types=entity_types)


def redact(
    text: str,
    entities: list[Entity] | None = None,
    engine: str = "regex",
    entity_types: list[str] | None = None,
    strategy: str = "token",
    preset: str | None = None,
) -> RedactResult:
    """
    v5-preview redaction entrypoint.

    If entities are provided, redact those spans. Otherwise, scan text first
    using the selected engine and redact the detected entities.
    """
    if preset is not None:
        try:
            strategy = _REDACT_PRESETS[preset]
        except KeyError as exc:
            allowed = ", ".join(sorted(_REDACT_PRESETS))
            raise ValueError(f"preset must be one of: {allowed}") from exc

    if entities is not None:
        return _redact_entities(text=text, entities=entities, strategy=strategy)

    return _scan_and_redact(
        text=text,
        engine=engine,
        entity_types=entity_types,
        strategy=strategy,
    )


def protect(
    entity_types: list[str] | None = None,
    engine: str = "regex",
    strategy: str = "token",
    on_detect: str = "redact",
):
    """
    v5-preview guardrail factory.
    """
    return create_guardrail(
        entity_types=entity_types,
        engine=engine,
        strategy=strategy,
        on_detect=on_detect,
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

    _lazy_import_regex_annotator()
    annotator = RegexAnnotator()
    # Use the structured output to get proper positions
    _, result = annotator.annotate_with_spans(text)

    # Convert to simple format, filtering out empty matches
    entities = []
    for span in result.spans:
        if span.text.strip():  # Only include non-empty matches
            entities.append(
                {
                    "type": span.label,
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


def process(text: str, anonymize: bool = False, method: str = "redact") -> dict:
    """
    Process text to detect and optionally anonymize PII.

    Args:
        text: Input text to process
        anonymize: Whether to anonymize detected PII
        method: Anonymization method ('redact', 'replace', 'hash')

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

    findings = _detect_impl(text)

    result = {"original": text, "findings": findings}

    if anonymize:
        anonymized = text
        # Simple anonymization - replace from end to start to preserve positions
        for finding in sorted(findings, key=lambda x: x["start"], reverse=True):
            start, end = finding["start"], finding["end"]
            entity_type = finding["type"]

            if method == "redact":
                replacement = f"[{entity_type}_REDACTED]"
            elif method == "replace":
                replacement = f"[{entity_type}_XXXXX]"
            elif method == "hash":
                import hashlib

                replacement = f"[{entity_type}_{hashlib.md5(finding['value'].encode()).hexdigest()[:8]}]"
            else:
                replacement = f"[{entity_type}]"

            anonymized = anonymized[:start] + replacement + anonymized[end:]

        result["anonymized"] = anonymized

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
