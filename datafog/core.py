"""
DataFog Core API - Lightweight PII detection functions.

This module provides simple, lightweight functions for PII detection and anonymization
without requiring heavy dependencies like spaCy or PyTorch.
"""

from typing import Dict, List, Union

from datafog.models.anonymizer import AnonymizerType

# Engine types as constants
REGEX_ENGINE = "regex"
SPACY_ENGINE = "spacy"
AUTO_ENGINE = "auto"


def detect_pii(text: str) -> Dict[str, List[str]]:
    """
    Simple PII detection using lightweight regex engine.

    Args:
        text: Text to scan for PII

    Returns:
        Dictionary mapping entity types to lists of detected values

    Example:
        >>> result = detect_pii("Contact john@example.com at (555) 123-4567")
        >>> print(result)
        {'EMAIL': ['john@example.com'], 'PHONE': ['(555) 123-4567']}
    """
    import time as _time

    _start = _time.monotonic()

    try:
        from datafog.services.text_service import TextService

        # Use lightweight regex engine only
        service = TextService(engine=REGEX_ENGINE)
        result = service.annotate_text_sync(text, structured=True)

        # Convert to simple dictionary format, filtering out empty matches
        pii_dict = {}
        for annotation in result:
            if annotation.text.strip():  # Only include non-empty matches
                entity_type = annotation.label
                if entity_type not in pii_dict:
                    pii_dict[entity_type] = []
                pii_dict[entity_type].append(annotation.text)

        try:
            from datafog.telemetry import (
                _get_duration_bucket,
                _get_text_length_bucket,
                track_function_call,
            )

            _duration = (_time.monotonic() - _start) * 1000
            entity_count = sum(len(v) for v in pii_dict.values())
            track_function_call(
                function_name="detect_pii",
                module="datafog.core",
                engine="regex",
                text_length_bucket=_get_text_length_bucket(len(text)),
                entity_count=entity_count,
                entity_types_found=list(pii_dict.keys()),
                duration_ms_bucket=_get_duration_bucket(_duration),
            )
        except Exception:
            pass

        return pii_dict

    except ImportError as e:
        try:
            from datafog.telemetry import track_error

            track_error("detect_pii", type(e).__name__, engine="regex")
        except Exception:
            pass
        raise ImportError(
            "Core dependencies missing. Install with: pip install datafog[all]"
        ) from e


def anonymize_text(text: str, method: Union[str, AnonymizerType] = "redact") -> str:
    """
    Simple text anonymization using lightweight regex engine.

    Args:
        text: Text to anonymize
        method: Anonymization method ('redact', 'replace', or 'hash')

    Returns:
        Anonymized text string

    Example:
        >>> result = anonymize_text("Contact john@example.com", method="redact")
        >>> print(result)
        "Contact [EMAIL_REDACTED]"
    """
    import time as _time

    _start = _time.monotonic()
    _method_str = method if isinstance(method, str) else method.value

    try:
        from datafog.models.anonymizer import Anonymizer, AnonymizerType
        from datafog.services.text_service import TextService

        # Convert string method to enum if needed
        if isinstance(method, str):
            method_map = {
                "redact": AnonymizerType.REDACT,
                "replace": AnonymizerType.REPLACE,
                "hash": AnonymizerType.HASH,
            }
            if method not in method_map:
                raise ValueError(
                    f"Invalid method: {method}. Use 'redact', 'replace', or 'hash'"
                )
            method = method_map[method]

        # Use lightweight regex engine only
        service = TextService(engine=REGEX_ENGINE)
        span_results = service.annotate_text_sync(text, structured=True)

        # Convert Span objects to AnnotationResult format for anonymizer, filtering empty matches
        from datafog.models.annotator import AnnotationResult

        annotations = []
        for span in span_results:
            if span.text.strip():  # Only include non-empty matches
                annotation = AnnotationResult(
                    entity_type=span.label,
                    start=span.start,
                    end=span.end,
                    score=1.0,  # Regex matches are certain
                    recognition_metadata=None,
                )
                annotations.append(annotation)

        # Create anonymizer and apply
        anonymizer = Anonymizer(anonymizer_type=method)
        result = anonymizer.anonymize(text, annotations)

        try:
            from datafog.telemetry import (
                _get_duration_bucket,
                _get_text_length_bucket,
                track_function_call,
            )

            _duration = (_time.monotonic() - _start) * 1000
            track_function_call(
                function_name="anonymize_text",
                module="datafog.core",
                method=_method_str,
                text_length_bucket=_get_text_length_bucket(len(text)),
                duration_ms_bucket=_get_duration_bucket(_duration),
            )
        except Exception:
            pass

        return result.anonymized_text

    except ImportError as e:
        try:
            from datafog.telemetry import track_error

            track_error("anonymize_text", type(e).__name__, method=_method_str)
        except Exception:
            pass
        raise ImportError(
            "Core dependencies missing. Install with: pip install datafog[all]"
        ) from e


def scan_text(
    text: str, return_entities: bool = False
) -> Union[bool, Dict[str, List[str]]]:
    """
    Quick scan to check if text contains any PII.

    Args:
        text: Text to scan
        return_entities: If True, return detected entities; if False, return boolean

    Returns:
        Boolean indicating PII presence, or dictionary of detected entities

    Example:
        >>> has_pii = scan_text("Contact john@example.com")
        >>> print(has_pii)
        True

        >>> entities = scan_text("Contact john@example.com", return_entities=True)
        >>> print(entities)
        {'EMAIL': ['john@example.com']}
    """
    import time as _time

    _start = _time.monotonic()

    entities = detect_pii(text)

    result = entities if return_entities else len(entities) > 0

    try:
        from datafog.telemetry import _get_duration_bucket, track_function_call

        _duration = (_time.monotonic() - _start) * 1000
        track_function_call(
            function_name="scan_text",
            module="datafog.core",
            return_entities=return_entities,
            duration_ms_bucket=_get_duration_bucket(_duration),
        )
    except Exception:
        pass

    return result


def get_supported_entities() -> List[str]:
    """
    Get list of PII entity types supported by the regex engine.

    Returns:
        List of supported entity type names

    Example:
        >>> entities = get_supported_entities()
        >>> print(entities)
        ['EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IP_ADDRESS', 'DOB', 'ZIP']
    """
    try:
        from datafog.processing.text_processing.regex_annotator.regex_annotator import (
            RegexAnnotator,
        )

        annotator = RegexAnnotator()
        result = [entity.value for entity in annotator.supported_entities]

        try:
            from datafog.telemetry import track_function_call

            track_function_call(
                function_name="get_supported_entities",
                module="datafog.core",
            )
        except Exception:
            pass

        return result

    except ImportError:
        # Fallback to basic list if imports fail
        return ["EMAIL", "PHONE", "SSN", "CREDIT_CARD", "IP_ADDRESS", "DOB", "ZIP"]


# Backward compatibility aliases
detect = detect_pii
process = anonymize_text
