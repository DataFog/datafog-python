import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from datafog.config import OperationType
from datafog.main import DataFog
from datafog.processing.text_processing.spacy_pii_annotator import (
    SpacyPIIAnnotator as TextPIIAnnotator,
)
from datafog.services.image_service import ImageService
from datafog.services.text_service import TextService


@pytest.fixture
def mock_image_service():
    with patch("datafog.main.ImageService") as mock:
        mock.return_value.ocr_extract = AsyncMock()
        yield mock.return_value


@pytest.fixture
def mock_text_service():
    with patch("datafog.main.TextService") as mock:
        mock.return_value.batch_annotate_text_async = AsyncMock()
        yield mock.return_value


@pytest.fixture
def text_annotator():
    return TextPIIAnnotator.create()


@pytest.fixture(scope="module")
def datafog():
    return DataFog()


@pytest.fixture(scope="module")
def image_url():
    with open("tests/image_set.json", "r") as f:
        return json.load(f)["executive_email"]


def test_text_pii_annotator(text_annotator):
    text = "Travis Kalanick lives at 1234 Elm St, Springfield."
    annotated_text = text_annotator.annotate(text)

    assert_annotation_results(annotated_text)
    assert_file_output(annotated_text)


def assert_annotation_results(annotated_text):
    assert annotated_text, "No results returned from annotation"
    assert "PERSON" in annotated_text, "No person detected"
    assert "LOC" in annotated_text, "No location detected"
    assert (
        "Travis Kalanick" in annotated_text["PERSON"]
    ), "Person not correctly identified"
    assert "1234 Elm St" in annotated_text["FAC"], "Facility not correctly identified"
    assert (
        "Springfield" in annotated_text["GPE"]
    ), "Geopolitical entity not correctly identified"


def assert_file_output(annotated_text):
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp:
        json.dump(annotated_text, temp)
        temp.flush()
        assert os.path.exists(temp.name), "Output file not created"
        with open(temp.name, "r") as f:
            file_content = json.load(f)
        assert (
            file_content == annotated_text
        ), "File output doesn't match returned annotation"
    os.unlink(temp.name)


def test_datafog_init():
    datafog = DataFog()
    assert isinstance(datafog.image_service, ImageService)
    assert isinstance(datafog.text_service, TextService)
    assert datafog.spark_service is None
    assert datafog.operations == [OperationType.ANNOTATE_PII]

    custom_image_service = ImageService()
    custom_text_service = TextService()
    custom_operations = [OperationType.ANNOTATE_PII, OperationType.REDACT_PII]

    datafog_custom = DataFog(
        image_service=custom_image_service,
        text_service=custom_text_service,
        operations=custom_operations,
    )

    assert datafog_custom.image_service == custom_image_service
    assert datafog_custom.text_service == custom_text_service
    assert datafog_custom.operations == custom_operations


@pytest.mark.asyncio
async def test_run_ocr_pipeline(mock_image_service, mock_text_service):
    datafog = DataFog(image_service=mock_image_service, text_service=mock_text_service)

    mock_image_service.ocr_extract.return_value = ["Extracted text"]
    mock_text_service.batch_annotate_text_async.return_value = {
        "PERSON": ["Satya Nadella"]
    }

    result = await datafog.run_ocr_pipeline(["image_url"])

    mock_image_service.ocr_extract.assert_called_once_with(["image_url"])
    mock_text_service.batch_annotate_text_async.assert_called_once_with(
        ["Extracted text"]
    )
    assert result == {"PERSON": ["Satya Nadella"]}


@pytest.mark.asyncio
async def test_run_text_pipeline(mock_text_service):
    datafog = DataFog(text_service=mock_text_service)

    mock_text_service.batch_annotate_text_async.return_value = {"PERSON": ["Elon Musk"]}

    result = await datafog.run_text_pipeline(
        ["Elon Musk tries one more time to save his $56 billion pay package"]
    )

    mock_text_service.batch_annotate_text_async.assert_called_once_with(
        ["Elon Musk tries one more time to save his $56 billion pay package"]
    )
    assert result == {"PERSON": ["Elon Musk"]}


@pytest.mark.asyncio
async def test_run_text_pipeline_no_annotation():
    datafog = DataFog(operations=[])

    result = await datafog.run_text_pipeline(["Sample text"])

    assert result == ["Sample text"]


def test_run_text_pipeline_sync(mock_text_service):
    datafog = DataFog(text_service=mock_text_service)

    mock_text_service.batch_annotate_text_sync.return_value = {"PERSON": ["Jeff Bezos"]}

    result = datafog.run_text_pipeline_sync(["Jeff Bezos steps down as Amazon CEO"])

    mock_text_service.batch_annotate_text_sync.assert_called_once_with(
        ["Jeff Bezos steps down as Amazon CEO"]
    )
    assert result == {"PERSON": ["Jeff Bezos"]}


def test_run_text_pipeline_sync_no_annotation():
    datafog = DataFog(operations=[])

    result = datafog.run_text_pipeline_sync(["Sample text"])

    assert result == ["Sample text"]
