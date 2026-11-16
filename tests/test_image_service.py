# Pytest tests for image_service.py

import asyncio

import pytest

from datafog.services.image_service import ImageService

Image = pytest.importorskip("PIL.Image", reason="Image tests require datafog[ocr]")

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
        successful_images = [img for img in images if isinstance(img, Image.Image)]
        failed_downloads = [img for img in images if isinstance(img, Exception)]

        print(f"Successful downloads: {len(successful_images)}")
        print(f"Failed downloads: {len(failed_downloads)}")

        for failed in failed_downloads:
            print(f"Download failed: {str(failed)}")

        assert len(successful_images) > 0, "No images were successfully downloaded"
        assert all(isinstance(image, Image.Image) for image in successful_images)
    finally:
        await asyncio.sleep(0)  # Yield control to event loop


@pytest.mark.asyncio
async def test_ocr_extract_with_tesseract():
    image_service2 = ImageService(use_tesseract=True, use_donut=False)
    texts = await image_service2.ocr_extract(urls)
    assert isinstance(texts, list)
    assert all(isinstance(text, str) for text in texts)


@pytest.mark.asyncio
async def test_ocr_extract_with_both():
    with pytest.raises(
        ValueError,
        match="Cannot use both Donut and Tesseract processors simultaneously",
    ):
        ImageService(use_tesseract=True, use_donut=True)


@pytest.mark.asyncio
async def test_ocr_extract_with_donut():
    image_service4 = ImageService(use_donut=True, use_tesseract=False)
    texts = await image_service4.ocr_extract(urls)
    assert isinstance(texts, list)
    assert all(isinstance(text, str) for text in texts)


@pytest.mark.asyncio
async def test_ocr_extract_no_processor_selected():
    with pytest.raises(ValueError, match="At least one OCR processor must be selected"):
        ImageService(use_tesseract=False, use_donut=False)
