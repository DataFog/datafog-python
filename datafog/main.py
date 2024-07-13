import json
import logging
from typing import List

from .config import OperationType
from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from .services.image_service import ImageService
from .services.spark_service import SparkService
from .services.text_service import TextService

logger = logging.getLogger("datafog_logger")
logger.setLevel(logging.INFO)


class DataFog:
    def __init__(
        self,
        image_service=ImageService(),
        text_service=TextService(),
        spark_service=None,
        operations: List[OperationType] = [OperationType.ANNOTATE_PII],
    ):
        self.image_service = image_service
        self.text_service = text_service
        self.spark_service: SparkService = spark_service
        self.operations: List[OperationType] = operations
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "Initializing DataFog class with the following services and operations:"
        )
        self.logger.info(f"Image Service: {type(image_service)}")
        self.logger.info(f"Text Service: {type(text_service)}")
        self.logger.info(
            f"Spark Service: {type(spark_service) if spark_service else 'None'}"
        )
        self.logger.info(f"Operations: {operations}")

    async def run_ocr_pipeline(self, image_urls: List[str]):
        """Run the OCR pipeline asynchronously on a list of images provided via url."""
        try:
            extracted_text = await self.image_service.ocr_extract(image_urls)
            self.logger.info(f"OCR extraction completed for {len(image_urls)} images.")
            self.logger.debug(
                f"Total length of extracted text: {sum(len(text) for text in extracted_text)}"
            )

            if OperationType.ANNOTATE_PII in self.operations:
                annotated_text = await self.text_service.batch_annotate_text_async(
                    extracted_text
                )
                self.logger.info(
                    f"Text annotation completed with {len(annotated_text)} annotations."
                )
                return annotated_text

            return extracted_text
        except Exception as e:
            self.logger.error(f"Error in run_ocr_pipeline: {str(e)}")
            raise

    async def run_text_pipeline(self, str_list: List[str]):
        """Run the text pipeline asynchronously on a list of input text."""
        try:
            self.logger.info(f"Starting text pipeline with {len(str_list)} texts.")
            if OperationType.ANNOTATE_PII in self.operations:
                annotated_text = await self.text_service.batch_annotate_text_async(
                    str_list
                )
                self.logger.info(
                    f"Text annotation completed with {len(annotated_text)} annotations."
                )
                return annotated_text

            self.logger.info("No annotation operation found; returning original texts.")
            return str_list
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline: {str(e)}")
            raise

    def run_text_pipeline_sync(self, str_list: List[str]):
        """Run the text pipeline synchronously on a list of input text."""
        try:
            self.logger.info(f"Starting text pipeline with {len(str_list)} texts.")
            if OperationType.ANNOTATE_PII in self.operations:
                annotated_text = self.text_service.batch_annotate_text_sync(str_list)
                self.logger.info(
                    f"Text annotation completed with {len(annotated_text)} annotations."
                )
                return annotated_text

            self.logger.info("No annotation operation found; returning original texts.")
            return str_list
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline: {str(e)}")
            raise

    def _add_attributes(self, attributes: dict):
        """Add multiple attributes."""
        for key, value in attributes.items():
            pass


class TextPIIAnnotator:
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
            pass
