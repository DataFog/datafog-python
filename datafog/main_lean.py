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
        self.operations: List[OperationType] = operations
        self.anonymizer = Anonymizer(
            hash_type=hash_type, anonymizer_type=anonymizer_type
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing lightweight DataFog class with regex engine")
        self.logger.info(f"Operations: {operations}")
        self.logger.info(f"Hash Type: {hash_type}")
        self.logger.info(f"Anonymizer Type: {anonymizer_type}")

    def run_text_pipeline_sync(self, str_list: List[str]) -> List[str]:
        """
        Run the text pipeline synchronously on a list of input text.

        Args:
            str_list (List[str]): A list of text strings to be processed.

        Returns:
            List[str]: Processed text results based on the enabled operations.

        Raises:
            Exception: Any error encountered during the text processing.
        """
        try:
            self.logger.info(f"Starting text pipeline with {len(str_list)} texts.")
            if OperationType.SCAN in self.operations:
                annotated_text = []

                for text in str_list:
                    # Use regex annotator for core PII detection
                    annotations = self.regex_annotator.annotate(text)
                    annotated_text.append(annotations)

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
                    return [
                        self.anonymizer.anonymize(text, annotations).anonymized_text
                        for text, annotations in zip(
                            str_list, annotated_text, strict=True
                        )
                    ]
                else:
                    return annotated_text

            self.logger.info(
                "No annotation or anonymization operation found; returning original texts."
            )
            return str_list
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline_sync: {str(e)}")
            raise

    def detect(self, text: str) -> dict:
        """
        Simple PII detection using regex patterns.

        Args:
            text: Input text to scan for PII

        Returns:
            Dictionary mapping entity types to lists of found entities
        """
        return self.regex_annotator.annotate(text)

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
        annotations = self.detect(text)

        result = {"original": text, "findings": annotations}

        if anonymize:
            if method == "redact":
                anonymizer_type = AnonymizerType.REDACT
            elif method == "replace":
                anonymizer_type = AnonymizerType.REPLACE
            elif method == "hash":
                anonymizer_type = AnonymizerType.HASH
            else:
                anonymizer_type = AnonymizerType.REDACT

            anonymized_result = self.anonymizer.anonymize(
                text, annotations, anonymizer_type
            )
            result["anonymized"] = anonymized_result.anonymized_text

        return result


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
