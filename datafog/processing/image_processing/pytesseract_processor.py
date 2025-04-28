"""
Provides OCR functionality using Pytesseract.

This module contains a PytesseractProcessor class for extracting text from images
using the Pytesseract OCR engine.
"""

import asyncio
import logging

import pytesseract
from PIL import Image


class PytesseractProcessor:
    """
    Processes images to extract text using Pytesseract OCR.

    Provides an asynchronous method to convert image content to text.
    Handles errors and logs issues during text extraction.
    """

    async def extract_text_from_image(self, image: Image.Image) -> str:
        try:
            # Run the blocking function in a separate thread
            return await asyncio.to_thread(pytesseract.image_to_string, image)
        except Exception as e:
            logging.error(f"Pytesseract error: {str(e)}")
            raise
