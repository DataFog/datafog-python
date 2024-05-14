import asyncio
import logging
from typing import List

import aiohttp
from PIL import Image

from datafog.processing.image_processing.donut_processor import DonutProcessor
from datafog.processing.image_processing.image_downloader import ImageDownloader
from datafog.processing.image_processing.pytesseract_processor import (
    PytesseractProcessor,
)


class ImageService:
    def __init__(self, use_donut: bool = False, use_tesseract: bool = True):
        self.downloader = ImageDownloader()
        self.use_donut = use_donut
        self.use_tesseract = use_tesseract
        self.donut_processor = DonutProcessor() if self.use_donut else None
        self.tesseract_processor = (
            PytesseractProcessor() if self.use_tesseract else None
        )

    async def download_images(self, urls: List[str]) -> List[Image.Image]:
        return await self.downloader.download_images(urls)

    async def ocr_extract(
        self,
        image_urls: List[str],
        image_files: List[Image.Image] = None,
    ) -> List[str]:
        if image_files is None:
            image_files = await self.download_images(image_urls)

        if self.use_donut and self.use_tesseract:
            raise ValueError("Both OCR processors cannot be selected simultaneously")

        if not self.use_donut and not self.use_tesseract:
            raise ValueError("No OCR processor selected")

        if self.use_donut:
            return await asyncio.gather(
                *[self.donut_processor.parse_image(image) for image in image_files]
            )

        if self.use_tesseract:
            return await asyncio.gather(
                *[
                    self.tesseract_processor.extract_text_from_image(image)
                    for image in image_files
                ]
            )
