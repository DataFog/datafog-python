# Pytest tests for image_service.py
# Tests the ImageService class
# ImageService downloads images and extracts text
# Uses ImageDownloader, DonutProcessor, PytesseractProcessor
# ImageService has two methods: download_images, ocr_extract
# download_images downloads images from URLs
# ocr_extract extracts text from images
# ocr_extract has optional params: use_donut, use_tesseract
# use_donut selects donut processor for OCR
# use_tesseract selects pytesseract processor for OCR


import asyncio

import pytest
from PIL import Image

from datafog.services.image_service import ImageService

urls = [
    "https://www.pdffiller.com/preview/101/35/101035394.png",
    "https://www.pdffiller.com/preview/435/972/435972694.png",
]


@pytest.mark.asyncio
async def test_download_images():
    image_service = ImageService()
    try:
        images = await image_service.download_images(urls)
        assert len(images) == 2
        assert all(isinstance(image, Image.Image) for image in images)
    finally:
        await asyncio.sleep(0)  # Allow pending callbacks to run


@pytest.mark.asyncio
async def test_ocr_extract_with_tesseract():
    image_service2 = ImageService(use_tesseract=True, use_donut=False)
    texts = await image_service2.ocr_extract(urls)
    assert isinstance(texts, list)
    assert all(isinstance(text, str) for text in texts)


@pytest.mark.asyncio
async def test_ocr_extract_with_both():
    image_service3 = ImageService(use_tesseract=True, use_donut=True)
    with pytest.raises(
        ValueError, match="Both OCR processors cannot be selected simultaneously"
    ):
        await image_service3.ocr_extract(urls)


@pytest.mark.asyncio
async def test_ocr_extract_with_donut():
    image_service4 = ImageService(use_donut=True, use_tesseract=False)
    texts = await image_service4.ocr_extract(urls)
    assert isinstance(texts, list)
    assert all(isinstance(text, str) for text in texts)


@pytest.mark.asyncio
async def test_ocr_extract_no_processor_selected():
    image_service5 = ImageService(use_tesseract=False, use_donut=False)
    with pytest.raises(ValueError, match="No OCR processor selected"):
        await image_service5.ocr_extract(urls)
