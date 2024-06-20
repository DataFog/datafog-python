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
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from azure.monitor.opentelemetry import configure_azure_monitor
import platform
from opentelemetry.trace import Status, StatusCode

# Use environment variable if available, otherwise fall back to hardcoded value
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from logging import INFO, getLogger
from dotenv import load_dotenv
import logging

load_dotenv()  # Load environment variables from .env file
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=00bea047-1836-46fa-9652-26d43d63a3fa;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/;ApplicationId=959cc365-c112-491b-af69-b196d0943ca4"
configure_azure_monitor(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING)
trace.set_tracer_provider(TracerProvider())
exporter = AzureMonitorTraceExporter(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))
logger = logging.getLogger("datafog_logger")
logger.setLevel(INFO)

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
        self.logger.info("Initializing DataFog class with the following services and operations:")
        self.logger.info(f"Image Service: {type(image_service)}")
        self.logger.info(f"Text Service: {type(text_service)}")
        self.logger.info(f"Spark Service: {type(spark_service) if spark_service else 'None'}")
        self.logger.info(f"Operations: {operations}")
        self.tracer = trace.get_tracer(__name__)

    async def run_ocr_pipeline(self, image_urls: List[str]):
        """Run the OCR pipeline asynchronously."""
        with self.tracer.start_as_current_span("run_ocr_pipeline") as span:
            try:
                extracted_text = await self.image_service.ocr_extract(image_urls)
                self.logger.info(f"OCR extraction completed for {len(image_urls)} images.")
                self.logger.debug(f"Total length of extracted text: {sum(len(text) for text in extracted_text)}")

                if OperationType.ANNOTATE_PII in self.operations:
                    annotated_text = await self.text_service.batch_annotate_texts(extracted_text)
                    self.logger.info(f"Text annotation completed with {len(annotated_text)} annotations.")
                    return annotated_text
                
                return extracted_text
            except Exception as e:
                self.logger.error(f"Error in run_ocr_pipeline: {str(e)}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    async def run_text_pipeline(self, texts: List[str]):
        """Run the text pipeline asynchronously."""
        with self.tracer.start_as_current_span("run_text_pipeline") as span:
            try:
                self.logger.info(f"Starting text pipeline with {len(texts)} texts.")
                if OperationType.ANNOTATE_PII in self.operations:
                    annotated_text = await self.text_service.batch_annotate_texts(texts)
                    self.logger.info(f"Text annotation completed with {len(annotated_text)} annotations.")
                    return annotated_text
                
                self.logger.info("No annotation operation found; returning original texts.")
                return texts
            except Exception as e:
                self.logger.error(f"Error in run_text_pipeline: {str(e)}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    def _add_attributes(self, span, attributes: dict):
        """Add multiple attributes to a span."""
        for key, value in attributes.items():
            span.set_attribute(key, value)


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
