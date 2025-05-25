"""
DataFog: Lightning-fast PII detection and anonymization library.

Core package provides regex-based PII detection with 190x performance advantage.
Optional extras available for advanced features:
- pip install datafog[nlp] - for spaCy integration
- pip install datafog[ocr] - for image/OCR processing
- pip install datafog[all] - for all features
"""

from .__about__ import __version__

# Core imports - always available
from .models.annotator import AnnotationResult, AnnotatorRequest
from .models.anonymizer import (
    AnonymizationResult,
    Anonymizer,
    AnonymizerRequest,
    AnonymizerType,
)
from .models.common import EntityTypes
from .processing.text_processing.regex_annotator import RegexAnnotator

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


# Simple API for core functionality
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
    annotator = RegexAnnotator()
    result = annotator.annotate(text)

    # Convert to simple format
    entities = []
    for entity_type, matches in result.items():
        for match in matches:
            entities.append(
                {
                    "type": entity_type,
                    "value": match,
                    "start": text.find(match),
                    "end": text.find(match) + len(match),
                }
            )

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
    findings = detect(text)

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

    return result


# Core exports
__all__ = [
    "__version__",
    "detect",
    "process",
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
