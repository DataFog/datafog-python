import asyncio
import io
import ssl
from typing import List

import aiohttp
import certifi
from PIL import Image

from datafog.processing.image_processing.donut_processor import DonutProcessor
from datafog.processing.image_processing.pytesseract_processor import (
    PytesseractProcessor,
)


class ImageDownloader:
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
    def __init__(self, use_donut: bool = False, use_tesseract: bool = True):
        self.downloader = ImageDownloader()
        self.use_donut = use_donut
        self.use_tesseract = use_tesseract
        self.donut_processor = DonutProcessor() if self.use_donut else None
        self.tesseract_processor = (
            PytesseractProcessor() if self.use_tesseract else None
        )

    async def download_images(self, urls: List[str]) -> List[Image.Image]:
        async def download_image(url: str) -> Image.Image:
            return await self.downloader.download_image(url)

        tasks = [asyncio.create_task(download_image(url)) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

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
