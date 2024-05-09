import pytest
from datafog import TextPIIAnnotator, OCRPIIAnnotator
import json

def test_text_pii_annotation():
    """Test the PII annotation functionality."""
    text = "John Doe lives at 1234 Elm St, Springfield."
    text_annotator = TextPIIAnnotator()
    annotated_text = text_annotator.run(text)
    assert "John Doe" in annotated_text, "PII not annotated correctly."


def ocr_pii_annotation():
    """Test the PII annotation functionality."""
    with open('tests/image_set.json', 'r') as f:
        image_set = json.load(f)
        image_url = image_set['executive_email']
    annotator = OCRPIIAnnotator()
    annotated_text = annotator.run(image_url)
    assert "Kevin Scott" in annotated_text, "PII not annotated correctly."
    assert "Satya Nadella" in annotated_text, "PII not annotated correctly."
    assert "Bill Gates" in annotated_text, "PII not annotated correctly."