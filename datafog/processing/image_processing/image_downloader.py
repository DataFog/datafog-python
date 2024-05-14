import asyncio
from io import BytesIO
from typing import List

import aiohttp
import requests
from PIL import Image


class ImageDownloader:
    def __init__(self):
        pass

    async def download_image(self, image_url: str) -> Image.Image:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    content = await response.read()
                    return Image.open(BytesIO(content)).convert("RGB")
                else:
                    raise Exception(f"Failed to download image from {image_url}")

    async def download_images(self, urls: List[str]) -> List[Image.Image]:
        return await asyncio.gather(*[self.download_image(url) for url in urls])
