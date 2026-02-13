"""
Asynchronous image downloader for fetching images from URLs.

This module provides functionality to download single or multiple images
asynchronously from given URLs using aiohttp.
"""

import asyncio
from io import BytesIO
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from PIL import Image


class ImageDownloader:
    """
    Asynchronous image downloader.

    Provides methods to download single or multiple images from URLs.
    Uses aiohttp for efficient asynchronous network operations.
    """

    def __init__(self):
        pass

    async def download_image(self, image_url: str) -> "Image.Image":
        """Download a single image from a URL."""
        try:
            import aiohttp
            from PIL import Image
        except ImportError as e:
            raise ModuleNotFoundError(
                "Image download requires optional dependencies. "
                "Install with: pip install datafog[web,ocr]"
            ) from e

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    content = await response.read()
                    return Image.open(BytesIO(content)).convert("RGB")
                else:
                    raise Exception(f"Failed to download image from {image_url}")

    async def download_images(self, urls: List[str]) -> List["Image.Image"]:
        """Download multiple images from a list of URLs concurrently."""
        return await asyncio.gather(*[self.download_image(url) for url in urls])
