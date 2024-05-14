import asyncio
import importlib
import json
import subprocess
import sys
from typing import List

import aiohttp

from .config import OperationType
from .processing.image_processing.donut_processor import DonutProcessor
from .processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from .services.image_service import ImageService
from .services.spark_service import SparkService
from .services.text_service import TextService


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

    async def run_ocr_pipeline(self, image_urls: List[str]):
        """Run the OCR pipeline asynchronously."""
        extracted_text = await self.image_service.ocr_extract(image_urls)
        if OperationType.ANNOTATE_PII in self.operations:
            annotated_text = await self.text_service.batch_annotate_texts(
                extracted_text
            )
            return annotated_text
        return extracted_text

    async def run_text_pipeline(self, texts: List[str]):
        """Run the text pipeline asynchronously."""
        if OperationType.ANNOTATE_PII in self.operations:
            annotated_text = await self.text_service.batch_annotate_texts(texts)
            return annotated_text
        return texts


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
