"""
Main module for DataFog.

This module contains the core classes for DataFog:
- DataFog: Main class for running OCR and text processing pipelines.
- TextPIIAnnotator: Class for annotating PII in text.

These classes provide high-level interfaces for image and text processing,
including OCR, PII detection, annotation, and anonymization.
"""

import json
import logging
from typing import List

from .config import OperationType
from .models.anonymizer import Anonymizer, AnonymizerType, HashType
from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from .services.image_service import ImageService
from .services.spark_service import SparkService
from .services.text_service import TextService

logger = logging.getLogger("datafog_logger")
logger.setLevel(logging.INFO)


class DataFog:
    """
    Main class for running OCR and text processing pipelines.

    Handles image and text processing operations, including OCR, PII detection, and anonymization.

    Attributes:
        image_service: Service for image processing and OCR.
        text_service: Service for text processing and annotation.
        spark_service: Optional Spark service for distributed processing.
        operations: List of operations to perform.
        anonymizer: Anonymizer for PII redaction, replacement, or hashing.
    """

    def __init__(
        self,
        image_service=None,
        text_service=None,
        spark_service=None,
        operations: List[OperationType] = [OperationType.SCAN],
        hash_type: HashType = HashType.SHA256,
        anonymizer_type: AnonymizerType = AnonymizerType.REPLACE,
    ):
        self.image_service = image_service or ImageService()
        self.text_service = text_service or TextService()
        self.spark_service: SparkService = spark_service
        self.operations: List[OperationType] = operations
        self.anonymizer = Anonymizer(
            hash_type=hash_type, anonymizer_type=anonymizer_type
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "Initializing DataFog class with the following services and operations:"
        )
        self.logger.info(f"Image Service: {type(self.image_service)}")
        self.logger.info(f"Text Service: {type(self.text_service)}")
        self.logger.info(
            f"Spark Service: {type(self.spark_service) if self.spark_service else 'None'}"
        )
        self.logger.info(f"Operations: {operations}")
        self.logger.info(f"Hash Type: {hash_type}")
        self.logger.info(f"Anonymizer Type: {anonymizer_type}")

    async def run_ocr_pipeline(self, image_urls: List[str]):
        """
        Run the OCR pipeline asynchronously on a list of images provided via URL.

        This method performs optical character recognition (OCR) on the images specified by the URLs.
        If PII annotation is enabled, it also annotates the extracted text for personally identifiable information.
        If redaction, replacement, or hashing is enabled, it applies the corresponding anonymization.

        Args:
            image_urls (List[str]): A list of URLs pointing to the images to be processed.

        Returns:
            List: Processed text results based on the enabled operations.

        Raises:
            Exception: Any error encountered during the OCR or text processing.
        """
        try:
            extracted_text = await self.image_service.ocr_extract(image_urls)
            self.logger.info(f"OCR extraction completed for {len(image_urls)} images.")

            return await self._process_text(extracted_text)
        except Exception as e:
            logging.error(f"Error in run_ocr_pipeline: {str(e)}")
            return [f"Error: {str(e)}"]

    async def run_text_pipeline(self, str_list: List[str]):
        """
        Run the text pipeline asynchronously on a list of input text.

        This method processes a list of text strings, potentially annotating them for personally
        identifiable information (PII) and applying anonymization if enabled.

        Args:
            str_list (List[str]): A list of text strings to be processed.

        Returns:
            List: Processed text results based on the enabled operations.

        Raises:
            Exception: Any error encountered during the text processing.
        """
        try:
            self.logger.info(f"Starting text pipeline with {len(str_list)} texts.")
            return await self._process_text(str_list)
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline: {str(e)}")
            raise

    async def _process_text(self, text_list: List[str]):
        """
        Internal method to process text based on enabled operations.
        """
        if OperationType.SCAN in self.operations:
            annotated_text = await self.text_service.batch_annotate_text_async(
                text_list
            )
            self.logger.info(
                f"Text annotation completed with {len(annotated_text)} annotations."
            )

            if OperationType.REDACT in self.operations:
                return [
                    self.anonymizer.anonymize(
                        text, annotations, AnonymizerType.REDACT
                    ).anonymized_text
                    for text, annotations in zip(text_list, annotated_text, strict=True)
                ]
            elif OperationType.REPLACE in self.operations:
                return [
                    self.anonymizer.anonymize(
                        text, annotations, AnonymizerType.REPLACE
                    ).anonymized_text
                    for text, annotations in zip(text_list, annotated_text, strict=True)
                ]
            elif OperationType.HASH in self.operations:
                return [
                    self.anonymizer.anonymize(
                        text, annotations, AnonymizerType.HASH
                    ).anonymized_text
                    for text, annotations in zip(text_list, annotated_text, strict=True)
                ]
            else:
                return annotated_text

        self.logger.info(
            "No annotation or anonymization operation found; returning original texts."
        )
        return text_list

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
                annotated_text = self.text_service.batch_annotate_text_sync(str_list)
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

    def _add_attributes(self, attributes: dict):
        """
        Add multiple attributes to the DataFog instance.

        This private method allows for the dynamic addition of multiple attributes to the
        DataFog instance. It iterates through the provided dictionary of attributes and
        adds each key-value pair as an attribute.

        Args:
            attributes (dict): A dictionary where keys are attribute names and values are
                               the corresponding attribute values to be added.

        Note:
            This method is intended for internal use and may be used for extending the
            functionality of the DataFog class dynamically. Care should be taken when
            using this method to avoid overwriting existing attributes.
        """
        for key, value in attributes.items():
            setattr(self, key, value)


class TextPIIAnnotator:
    """
    Class for annotating PII in text.

    Provides functionality to detect and annotate Personally Identifiable Information (PII) in text.

    Attributes:
        text_annotator: SpacyPIIAnnotator instance for text annotation.
        spark_processor: Optional SparkService for distributed processing.
    """

    def __init__(self):
        self.text_annotator = SpacyPIIAnnotator.create()
        self.spark_processor: SparkService = None

    def run(self, text, output_path=None):
        try:
            annotated_text = self.text_annotator.annotate(text)

            # Optionally, output the results to a JSON file
            if output_path:
                with open(output_path, "w") as f:
                    json.dump(annotated_text, f)

            return annotated_text

        finally:
            # Ensure Spark resources are released
            if self.spark_processor:
                self.spark_processor.stop()
