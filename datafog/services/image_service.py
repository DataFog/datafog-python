"""
Image processing service for OCR and other operations.

This module provides classes for downloading images and performing OCR using
either Tesseract or Donut models. It supports processing both local images
and images from URLs.
"""

import asyncio
import io
import logging
import os
import ssl
from typing import List, Union

import aiohttp
import certifi
from PIL import Image

from datafog.processing.image_processing.donut_processor import DonutProcessor
from datafog.processing.image_processing.pytesseract_processor import (
    PytesseractProcessor,
)

# Check if the PYTEST_DONUT flag is set to enable OCR testing
DONUT_TESTING_ENABLED = os.environ.get("PYTEST_DONUT", "").lower() == "yes"


class ImageDownloader:
    """Asynchronous image downloader with SSL support."""

    async def download_image(self, url: str) -> Image.Image:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(io.BytesIO(image_data))
                else:
                    raise Exception(
                        f"Failed to download image. Status code: {response.status}"
                    )


class ImageService:
    """
    Service for image processing and OCR.

    Supports Tesseract and Donut OCR models, image downloading,
    and various image processing operations.
    """

    def __init__(self, use_donut: bool = False, use_tesseract: bool = True):
        self.downloader = ImageDownloader()

        # Check if we're in a test environment
        in_test_env = (
            "PYTEST_CURRENT_TEST" in os.environ or "TOX_ENV_NAME" in os.environ
        )

        # Log the initial OCR processor selection
        logging.info(
            f"Initial OCR processor selection: use_donut={use_donut}, use_tesseract={use_tesseract}"
        )

        # In test environment without PYTEST_DONUT=yes, we should still allow Donut for testing
        # but the DonutProcessor will return mock results
        if in_test_env:
            if DONUT_TESTING_ENABLED:
                logging.info(
                    "PYTEST_DONUT=yes is set, enabling real Donut OCR in test environment"
                )
            else:
                logging.info(
                    "Test environment detected without PYTEST_DONUT=yes, Donut will use mock results"
                )

        if use_donut and use_tesseract:
            raise ValueError(
                "Cannot use both Donut and Tesseract processors simultaneously."
            )

        if not use_donut and not use_tesseract:
            raise ValueError("At least one OCR processor must be selected.")

        self.use_donut = use_donut
        self.use_tesseract = use_tesseract

        # Only create the processors if they're going to be used
        # This ensures torch/transformers are only imported when needed
        self.donut_processor = DonutProcessor() if self.use_donut else None
        self.tesseract_processor = (
            PytesseractProcessor() if self.use_tesseract else None
        )

    async def download_images(
        self, urls: List[str]
    ) -> List[Union[Image.Image, BaseException]]:
        tasks = [
            asyncio.create_task(self.downloader.download_image(url)) for url in urls
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def ocr_extract(self, image_paths: List[str]) -> List[str]:
        results = []
        for path in image_paths:
            try:
                if os.path.isfile(path):
                    # Local file
                    with Image.open(path) as img:
                        img.verify()  # Verify the image
                    image = Image.open(path)
                else:
                    # URL
                    image = await self.downloader.download_image(path)

                if self.use_tesseract and self.tesseract_processor is not None:
                    text = await self.tesseract_processor.extract_text_from_image(image)
                elif self.use_donut and self.donut_processor is not None:
                    text = await self.donut_processor.extract_text_from_image(image)
                else:
                    raise ValueError("No OCR processor selected")

                results.append(text)
            except Exception as e:
                error_msg = f"Error processing image {path}: {str(e)}"
                logging.error(error_msg)
                results.append(error_msg)

        return results

    async def process_images(self, image_urls, operation):
        results = []
        for url in image_urls:
            logging.info(f"Fetching image from {url}")
            image = await self.downloader.download_image(url)
            logging.info(f"Processing image with operation: {operation}")
            result = await self.process_image(image, operation)
            results.append(result)
        return results

    async def process_image(self, image, operation):
        # Implement image processing logic
        logging.info(f"Processed image with operation: {operation}")
        pass
