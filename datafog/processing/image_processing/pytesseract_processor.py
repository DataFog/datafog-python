"""
Provides OCR functionality using Pytesseract.

This module contains a PytesseractProcessor class for extracting text from images
using the Pytesseract OCR engine.
"""

import logging

import pytesseract
from PIL import Image

from datafog._legacy_retirement import warn_legacy_surface


class PytesseractProcessor:
    """
    Processes images to extract text using Pytesseract OCR.

    Provides an asynchronous method to convert image content to text.
    Handles errors and logs issues during text extraction.
    """

    async def extract_text_from_image(self, image: Image.Image) -> str:
        warn_legacy_surface("OCR")
        try:
            return pytesseract.image_to_string(image)
        except Exception as e:
            logging.error(f"Pytesseract error: {str(e)}")
            raise
