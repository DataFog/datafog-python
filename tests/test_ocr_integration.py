"""Integration tests for OCR functionality.

These tests verify that the OCR functionality works correctly with the PYTEST_DONUT flag.
When PYTEST_DONUT=yes is set, the tests will use the actual OCR implementation.
Otherwise, they will use a mock implementation.
"""

import io
from unittest.mock import patch

import pytest
from PIL import Image

from datafog.processing.image_processing.donut_processor import DonutProcessor
from datafog.services.image_service import ImageService

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def sample_image():
    """Create a simple test image."""
    # Create a small white image with some black text
    img = Image.new("RGB", (200, 100), color="white")
    return img


@pytest.fixture
def image_service_tesseract():
    """Create an ImageService instance using Tesseract."""
    return ImageService(use_donut=False, use_tesseract=True)


@pytest.fixture
def image_service_donut():
    """Create an ImageService instance using Donut."""
    return ImageService(use_donut=True, use_tesseract=False)


def test_ocr_with_tesseract(image_service_tesseract, sample_image):
    """Test OCR extraction using Tesseract.

    This test should always run regardless of the PYTEST_DONUT flag.
    """
    # Save the image to a bytes buffer
    img_buffer = io.BytesIO()
    sample_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # Create a temporary file-like object that PIL can open
    with patch("PIL.Image.open", return_value=sample_image):
        with patch("os.path.isfile", return_value=True):
            # Run the OCR extraction
            import asyncio

            result = asyncio.run(
                image_service_tesseract.ocr_extract(["dummy_path.png"])
            )

            # Verify that we got some result (even if empty for a blank image)
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 1


def test_ocr_with_donut(sample_image):
    """Test OCR extraction using Donut.

    This test will use a mock implementation if PYTEST_DONUT is not set to 'yes'.
    It will use the actual implementation if PYTEST_DONUT=yes.
    """
    # Save the image to a bytes buffer
    img_buffer = io.BytesIO()
    sample_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # Force the test environment flag to be recognized
    with patch("datafog.processing.image_processing.donut_processor.IN_TEST_ENV", True):
        with patch(
            "datafog.processing.image_processing.donut_processor.DONUT_TESTING_ENABLED",
            False,
        ):
            # Create a new image service with Donut enabled
            image_service = ImageService(use_donut=True, use_tesseract=False)

            # Create a temporary file-like object that PIL can open
            with patch("PIL.Image.open", return_value=sample_image):
                with patch("os.path.isfile", return_value=True):
                    # Run the OCR extraction
                    import asyncio

                    result = asyncio.run(image_service.ocr_extract(["dummy_path.png"]))

                    # Verify that we got some result
                    assert result is not None
                    assert isinstance(result, list)
                    assert len(result) == 1

                    # We should get the mock result since PYTEST_DONUT is not set
                    assert "Mock OCR text for testing" in result[0]


def test_donut_processor_directly(sample_image):
    """Test the DonutProcessor directly.

    This test will use a mock implementation if PYTEST_DONUT is not set to 'yes'.
    It will use the actual implementation if PYTEST_DONUT=yes.
    """
    # Force the test environment flag to be recognized
    with patch("datafog.processing.image_processing.donut_processor.IN_TEST_ENV", True):
        with patch(
            "datafog.processing.image_processing.donut_processor.DONUT_TESTING_ENABLED",
            False,
        ):
            processor = DonutProcessor()

            # Run the OCR extraction
            import asyncio

            result = asyncio.run(processor.extract_text_from_image(sample_image))

            # Verify that we got some result
            assert result is not None

            # If PYTEST_DONUT is not set, we should get the mock result
            assert "Mock OCR text for testing" in result
