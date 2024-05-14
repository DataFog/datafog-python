import pytesseract
from PIL import Image


class PytesseractProcessor:
    def __init__(self):
        pass

    @staticmethod
    async def extract_text_from_image(image: Image) -> str:
        """Extract text from an image using pytesseract."""
        return pytesseract.image_to_string(image)
