"""
Lean main module for DataFog core functionality.

This module contains the lightweight core classes for DataFog:
- DataFog: Main class for regex-based PII detection
- TextPIIAnnotator: Class for annotating PII in text using regex patterns

These classes provide the core PII detection functionality without heavy dependencies.
"""

import json
import logging
from typing import List

from .config import OperationType
from .engine import scan, scan_and_redact
from .models.anonymizer import Anonymizer, AnonymizerType, HashType
from .processing.text_processing.regex_annotator import RegexAnnotator

logger = logging.getLogger("datafog_logger")
logger.setLevel(logging.INFO)


class DataFog:
    """
    Lightweight main class for regex-based PII detection and anonymization.

    Handles text processing operations using fast regex patterns for PII detection.
    For advanced features like OCR, spaCy, or Spark, install additional extras.

    Attributes:
        regex_annotator: Core regex-based PII annotator.
        operations: List of operations to perform.
        anonymizer: Anonymizer for PII redaction, replacement, or hashing.
    """

    def __init__(
        self,
        operations: List[OperationType] = [OperationType.SCAN],
        hash_type: HashType = HashType.SHA256,
        anonymizer_type: AnonymizerType = AnonymizerType.REPLACE,
    ):
        self.regex_annotator = RegexAnnotator()
        normalized_ops: List[OperationType] = []
        for op in operations:
            if isinstance(op, OperationType):
                normalized_ops.append(op)
            elif isinstance(op, str):
                normalized_ops.append(OperationType(op.strip()))
            else:
                raise ValueError(f"Unsupported operation type: {type(op)!r}")

        self.operations: List[OperationType] = normalized_ops
        self.anonymizer = Anonymizer(
            hash_type=hash_type, anonymizer_type=anonymizer_type
        )
        self.hash_type = hash_type
        self.anonymizer_type = anonymizer_type
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing lightweight DataFog class with regex engine")
        self.logger.info(f"Operations: {self.operations}")
        self.logger.info(f"Hash Type: {hash_type}")
        self.logger.info(f"Anonymizer Type: {anonymizer_type}")

        try:
            from .telemetry import track_function_call

            track_function_call(
                function_name="DataFog.__init__",
                module="datafog.main",
                operations=[op.value for op in self.operations],
                hash_type=hash_type.value,
                anonymizer_type=anonymizer_type.value,
            )
        except Exception:
            pass

    async def run_ocr_pipeline(self, image_urls: List[str]) -> List[str]:
        """Run OCR + text pipeline for CLI/backward compatibility."""
        from .services.image_service import ImageService

        image_service = ImageService()
        extracted_text = await image_service.ocr_extract(image_urls)
        return self.run_text_pipeline_sync(extracted_text)

    def run_text_pipeline_sync(self, str_list: List[str]) -> List:
        """
        Run the text pipeline synchronously on a list of input text.

        Args:
            str_list (List[str]): A list of text strings to be processed.

        Returns:
            List[str]: Processed text results based on the enabled operations.

        Raises:
            Exception: Any error encountered during the text processing.
        """
        import time as _time

        _start = _time.monotonic()
        try:
            self.logger.info(f"Starting text pipeline with {len(str_list)} texts.")
            if OperationType.SCAN in self.operations:
                annotated_text = [self.detect(text) for text in str_list]

                self.logger.info(
                    f"Text annotation completed with {len(annotated_text)} annotations."
                )

                if any(
                    op in self.operations
                    for op in [
                        OperationType.REDACT,
                        OperationType.REPLACE,
                        OperationType.HASH,
                    ]
                ):
                    anonymized_results = []
                    for text in str_list:
                        if OperationType.HASH in self.operations:
                            method = "hash"
                        elif OperationType.REPLACE in self.operations:
                            method = "replace"
                        else:
                            method = "redact"
                        process_result = self.process(
                            text, anonymize=True, method=method
                        )
                        anonymized_results.append(process_result["anonymized"])

                    _pipeline_result = anonymized_results
                else:
                    _pipeline_result = annotated_text
            else:
                self.logger.info(
                    "No annotation or anonymization operation found; returning original texts."
                )
                _pipeline_result = str_list

            try:
                from .telemetry import _get_duration_bucket, track_function_call

                _duration = (_time.monotonic() - _start) * 1000
                track_function_call(
                    function_name="DataFog.run_text_pipeline_sync",
                    module="datafog.main",
                    batch_size=len(str_list),
                    operations=[op.value for op in self.operations],
                    duration_ms_bucket=_get_duration_bucket(_duration),
                )
            except Exception:
                pass

            return _pipeline_result
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline_sync: {str(e)}")
            try:
                from .telemetry import track_error

                track_error(
                    "DataFog.run_text_pipeline_sync",
                    type(e).__name__,
                    engine="regex",
                )
            except Exception:
                pass
            raise

    def detect(self, text: str) -> dict:
        """
        Simple PII detection using regex patterns.

        Args:
            text: Input text to scan for PII

        Returns:
            Dictionary mapping entity types to lists of found entities
        """
        import time as _time

        _start = _time.monotonic()

        scan_result = scan(text=text, engine="regex")
        result = {label: [] for label in RegexAnnotator.LABELS}
        legacy_map = {"DATE": "DOB", "ZIP_CODE": "ZIP"}
        for entity in scan_result.entities:
            label = legacy_map.get(entity.type, entity.type)
            result.setdefault(label, []).append(entity.text)

        try:
            from .telemetry import (
                _get_duration_bucket,
                _get_text_length_bucket,
                track_function_call,
            )

            _duration = (_time.monotonic() - _start) * 1000
            entity_count = sum(len(v) for v in result.values())
            track_function_call(
                function_name="DataFog.detect",
                module="datafog.main",
                text_length_bucket=_get_text_length_bucket(len(text)),
                entity_count=entity_count,
                duration_ms_bucket=_get_duration_bucket(_duration),
            )
        except Exception:
            pass

        return result

    def scan_text(self, text: str) -> dict:
        """Backward-compatible alias for simple text scanning."""
        return self.detect(text)

    def process(
        self, text: str, anonymize: bool = False, method: str = "redact"
    ) -> dict:
        """
        Process text to detect and optionally anonymize PII.

        Args:
            text: Input text to process
            anonymize: Whether to anonymize detected PII
            method: Anonymization method ('redact', 'replace', 'hash')

        Returns:
            Dictionary with original text, anonymized text (if requested), and findings
        """
        import time as _time

        _start = _time.monotonic()

        annotations_dict = self.detect(text)

        result = {"original": text, "findings": annotations_dict}

        if anonymize:
            strategy_map = {
                "redact": "token",
                "replace": "pseudonymize",
                "hash": "hash",
            }
            strategy = strategy_map.get(method, "token")
            redact_result = scan_and_redact(
                text=text,
                engine="regex",
                strategy=strategy,
            )
            result["anonymized"] = redact_result.redacted_text

        try:
            from .telemetry import _get_duration_bucket, track_function_call

            _duration = (_time.monotonic() - _start) * 1000
            track_function_call(
                function_name="DataFog.process",
                module="datafog.main",
                anonymize=anonymize,
                method=method,
                duration_ms_bucket=_get_duration_bucket(_duration),
            )
        except Exception:
            pass

        return result

    def process_text(self, text: str):
        """Backward-compatible helper mirroring pipeline behavior for one text."""
        if not self.operations:
            return text
        if any(
            op in self.operations
            for op in [OperationType.REDACT, OperationType.REPLACE, OperationType.HASH]
        ):
            return self.run_text_pipeline_sync([text])[0]
        return self.detect(text)


class TextPIIAnnotator:
    """
    Lightweight class for annotating PII in text using regex patterns.

    Provides functionality to detect and annotate Personally Identifiable Information (PII)
    in text using fast regex patterns instead of heavy NLP models.

    Attributes:
        regex_annotator: RegexAnnotator instance for text annotation.
    """

    def __init__(self):
        self.regex_annotator = RegexAnnotator()

    def run(self, text, output_path=None):
        """
        Run PII annotation on text using regex patterns.

        Args:
            text: Input text to annotate
            output_path: Optional path to save results as JSON

        Returns:
            Dictionary mapping entity types to lists of found entities
        """
        try:
            annotated_text = self.regex_annotator.annotate(text)

            # Optionally, output the results to a JSON file
            if output_path:
                with open(output_path, "w") as f:
                    json.dump(annotated_text, f)

            return annotated_text

        except Exception as e:
            logging.error(f"Error in TextPIIAnnotator.run: {str(e)}")
            raise
