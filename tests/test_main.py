import json

import pytest

from datafog import OCRPIIAnnotator, TextPIIAnnotator


def test_text_pii_annotation():
    """Test the PII annotation functionality."""
    text = "John Doe lives at 1234 Elm St, Springfield."
    text_annotator = TextPIIAnnotator()
    annotated_text = text_annotator.run(text)
    assert "Springfield" in annotated_text["LOC"], "PII not annotated correctly."


def test_ocr_pii_annotation():
    """Test the PII annotation functionality."""
    with open("tests/image_set.json", "r") as f:
        image_set = json.load(f)
        image_url = image_set["executive_email"]
    annotator = OCRPIIAnnotator()
    annotated_text = annotator.run(image_url)
    assert "Satya Nadella" in annotated_text["PER"], "PII not annotated correctly."
