import json

import pytest

from datafog import DataFog, TextPIIAnnotator


def search_nested_dict(d, target):
    """Recursively search for a target value in nested dictionaries."""
    if isinstance(d, dict):
        for key, value in d.items():
            if target in value:
                return True
            elif isinstance(value, dict):
                if search_nested_dict(value, target):
                    return True
    return False


def test_textpii_annotator():
    """Test the PII annotation functionality."""
    text = "John Doe lives at 1234 Elm St, Springfield."
    text_annotator = TextPIIAnnotator()
    annotated_text = text_annotator.run(text)
    assert "Springfield" in annotated_text["LOC"], "PII not annotated correctly."


# @pytest.mark.asyncio
# async def test_donut_processor():
#     """Test the PII annotation functionality for the donutprocessor."""
#     with open("tests/image_set.json", "r") as f:
#         image_set = json.load(f)
#         image_url = image_set["executive_email"]
#     ocr_annotator = OCRPIIAnnotator()
#     annotated_text = await ocr_annotator.run([image_url])
#     assert "Satya Nadella" in annotated_text[0].get("PER", []), "PII not annotated correctly."


@pytest.mark.asyncio
async def test_datafog_text_annotation():
    """Test DataFog class for text annotation."""
    text = ["Joe Biden is the President of the United States."]
    datafog = DataFog()
    annotated_text = await datafog.run_text_pipeline(text)

    assert annotated_text  # Ensure that some results are returned.
    assert search_nested_dict(
        annotated_text, "Joe Biden"
    ), "Joe Biden not found in annotated results."
    assert search_nested_dict(
        annotated_text, "the United States"
    ), "United States not found in annotated results."


@pytest.mark.asyncio
async def test_datafog_image_extraction():
    """Test DataFog class for image text extraction."""
    with open("tests/image_set.json", "r") as f:
        image_set = json.load(f)
        image_url = image_set["executive_email"]
    datafog = DataFog()
    extracted_text = await datafog.run_ocr_pipeline([image_url])
    assert extracted_text, "No text extracted."
    assert search_nested_dict(
        extracted_text, "Satya Nadella"
    ), "Satya Nadella not found in extracted text."


@pytest.mark.asyncio
async def test_datafog_image_annotation():
    """Test DataFog class for image text annotation."""
    with open("tests/image_set.json", "r") as f:
        image_set = json.load(f)
        image_url = image_set["executive_email"]
    datafog = DataFog()
    annotated_text = await datafog.run_ocr_pipeline([image_url])
    assert search_nested_dict(
        annotated_text, "Satya Nadella"
    ), "Satya Nadella not found in annotated text."
