import json
import logging
from logging import INFO
from typing import List

from .config import OperationType
from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from .services.image_service import ImageService
from .services.spark_service import SparkService
from .services.text_service import TextService
logger = logging.getLogger("datafog_logger")
logger.setLevel(INFO)


class DataFog:
    def __init__(
        self,
        image_service = ImageService(),
        text_service = TextService(),
        spark_service = None,
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
        """Run the OCR pipeline asynchronously."""
        try:
            extracted_text = await self.image_service.ocr_extract(image_urls)
            self.logger.info(f"OCR extraction completed for {len(image_urls)} images.")
            self.logger.debug(
                f"Total length of extracted text: {sum(len(text) for text in extracted_text)}"
            )

            if OperationType.ANNOTATE_PII in self.operations:
                annotated_text = await self.text_service.batch_annotate_texts(
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

    async def run_text_pipeline(self, texts: List[str]):
        """Run the text pipeline asynchronously."""
        try:
            self.logger.info(f"Starting text pipeline with {len(texts)} texts.")
            if OperationType.ANNOTATE_PII in self.operations:
                annotated_text = await self.text_service.batch_annotate_texts(texts)
                self.logger.info(
                    f"Text annotation completed with {len(annotated_text)} annotations."
                )
                return annotated_text

            self.logger.info("No annotation operation found; returning original texts.")
            return texts
        except Exception as e:
            self.logger.error(f"Error in run_text_pipeline: {str(e)}")
            raise

    def _add_attributes(self, attributes: dict):
        """Add multiple attributes."""
        for key, value in attributes.items():
            pass


class OCRPIIAnnotator:
    def __init__(self):
        self.image_service = ImageService(use_donut=True, use_tesseract=False)
        self.text_annotator = SpacyPIIAnnotator.create()
        self.spark_service: SparkService = None

    async def run(self, image_urls: List[str], output_path=None):
        try:
            # Download and process the image to extract text
            # downloaded_images = await self.image_service.download_images(image_urls)
            # extracted_texts = await self.image_service.ocr_extract(downloaded_images)

            # # Annotate the extracted text for PII
            # annotated_texts = [self.text_annotator.annotate(text) for text in extracted_texts]

            # # Optionally, output the results to a JSON file
            # if output_path:
            #     with open(output_path, "w") as f:
            #         json.dump(annotated_texts, f)

            # return annotated_texts
            pass

        finally:
            # Ensure Spark resources are released
            # self.spark_processor.spark.stop()
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
