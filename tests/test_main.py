import json
import logging
import re
from unittest.mock import AsyncMock, patch

import pytest

from datafog.config import OperationType
from datafog.main import DataFog
from datafog.models.annotator import AnnotationResult
from datafog.models.anonymizer import AnonymizerType, HashType

# Try to import optional dependencies
try:
    from datafog.processing.text_processing.spacy_pii_annotator import (
        SpacyPIIAnnotator as TextPIIAnnotator,
    )
    from datafog.services.image_service import ImageService
    from datafog.services.text_service import TextService

    HAS_FULL_DEPS = True
except ImportError:
    HAS_FULL_DEPS = False
    TextPIIAnnotator = None
    ImageService = None
    TextService = None

# Try to import the full-featured DataFog for integration tests
try:
    from datafog.main_original import DataFog as FullDataFog

    HAS_ORIGINAL_MAIN = True
except ImportError:
    HAS_ORIGINAL_MAIN = False
    FullDataFog = None


@pytest.fixture
def mock_image_service():
    if not HAS_FULL_DEPS:
        pytest.skip("Full dependencies not available")
    with patch("datafog.services.image_service.ImageService") as mock:
        mock.return_value.ocr_extract = AsyncMock()
        yield mock.return_value


@pytest.fixture
def mock_text_service():
    if not HAS_FULL_DEPS:
        pytest.skip("Full dependencies not available")
    with patch("datafog.services.text_service.TextService") as mock:
        mock.return_value.batch_annotate_text_async = AsyncMock()
        mock.return_value.batch_annotate_text_sync.return_value = [
            {"PERSON": ["Test Person"]}
        ]
        yield mock.return_value


@pytest.fixture
def text_annotator():
    if not HAS_FULL_DEPS:
        pytest.skip("Full dependencies not available")
    return TextPIIAnnotator.create()


@pytest.fixture(scope="module")
def datafog():
    return DataFog()


@pytest.fixture(scope="module")
def image_url():
    with open("tests/image_set.json", "r") as f:
        return json.load(f)["executive_email"]


@pytest.mark.skipif(not HAS_FULL_DEPS, reason="Full dependencies not available")
def test_text_pii_annotator(text_annotator):
    text = "Travis Kalanick lives at 1234 Elm St, Springfield."
    annotated_text = text_annotator.annotate(text)

    assert_annotation_results(annotated_text)
    assert_file_output(annotated_text)


def assert_annotation_results(annotated_text):
    assert annotated_text, "No results returned from annotation"
    assert "PERSON" in annotated_text, "No person detected"
    assert (
        "Travis Kalanick" in annotated_text["PERSON"]
    ), "Person not correctly identified"
    assert (
        "Springfield" in annotated_text["GPE"]
    ), "Geopolitical entity not correctly identified"

    # Address/facility detection can be inconsistent in spaCy across different environments
    # Check if the address is detected in any location-related entity type
    address_found = (
        ("FAC" in annotated_text and "1234 Elm St" in annotated_text["FAC"])
        or ("LOC" in annotated_text and "1234 Elm St" in annotated_text["LOC"])
        or ("GPE" in annotated_text and "1234 Elm St" in annotated_text["GPE"])
        or (
            "CARDINAL" in annotated_text
            and any("1234" in addr for addr in annotated_text["CARDINAL"])
        )
    )
    assert (
        address_found
    ), f"Address '1234 Elm St' not found in any location entity. Found entities: {list(annotated_text.keys())}"


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
    """Test the lean DataFog initialization."""
    datafog = DataFog()
    # Test lean version attributes
    assert hasattr(datafog, "regex_annotator")
    assert hasattr(datafog, "operations")
    assert hasattr(datafog, "anonymizer")
    assert datafog.operations == [OperationType.SCAN]


@pytest.mark.skipif(
    not HAS_FULL_DEPS or not HAS_ORIGINAL_MAIN, reason="Full dependencies not available"
)
def test_full_datafog_init():
    """Test the full-featured DataFog initialization when dependencies are available."""
    datafog = FullDataFog()
    assert isinstance(datafog.image_service, ImageService)
    assert isinstance(datafog.text_service, TextService)
    assert datafog.spark_service is None
    assert datafog.operations == [OperationType.SCAN]

    custom_image_service = ImageService()
    custom_text_service = TextService()
    custom_operations = [OperationType.SCAN, OperationType.REDACT]

    datafog_custom = FullDataFog(
        image_service=custom_image_service,
        text_service=custom_text_service,
        operations=custom_operations,
    )

    assert datafog_custom.image_service == custom_image_service
    assert datafog_custom.text_service == custom_text_service
    assert datafog_custom.operations == custom_operations


@pytest.mark.skipif(
    not HAS_FULL_DEPS or not HAS_ORIGINAL_MAIN, reason="Full dependencies not available"
)
@pytest.mark.asyncio
async def test_run_ocr_pipeline(mock_image_service, mock_text_service):
    datafog = FullDataFog(
        image_service=mock_image_service, text_service=mock_text_service
    )

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


@pytest.mark.skipif(
    not HAS_FULL_DEPS or not HAS_ORIGINAL_MAIN, reason="Full dependencies not available"
)
@pytest.mark.asyncio
async def test_run_text_pipeline(mock_text_service):
    datafog = FullDataFog(text_service=mock_text_service)

    mock_text_service.batch_annotate_text_async.return_value = {"PERSON": ["Elon Musk"]}

    result = await datafog.run_text_pipeline(
        ["Elon Musk tries one more time to save his $56 billion pay package"]
    )

    mock_text_service.batch_annotate_text_async.assert_called_once_with(
        ["Elon Musk tries one more time to save his $56 billion pay package"]
    )
    assert result == {"PERSON": ["Elon Musk"]}


@pytest.mark.skipif(not HAS_ORIGINAL_MAIN, reason="Full main module not available")
@pytest.mark.asyncio
async def test_run_text_pipeline_no_annotation():
    datafog = FullDataFog(operations=[])

    result = await datafog.run_text_pipeline(["Sample text"])

    assert result == ["Sample text"]


def test_run_text_pipeline_sync():
    """Test lean DataFog run_text_pipeline_sync with regex annotator."""
    datafog = DataFog()

    # Test with sample text containing PII
    test_text = "Contact john@example.com or call (555) 123-4567"
    result = datafog.run_text_pipeline_sync([test_text])

    # Should return annotations (dict format) since default is scan only
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], dict)


def test_run_text_pipeline_sync_no_annotation():
    """Test lean DataFog with no annotation operations."""
    datafog = DataFog(operations=[])

    result = datafog.run_text_pipeline_sync(["Sample text"])

    assert result == ["Sample text"]


@pytest.mark.skipif(
    not HAS_FULL_DEPS or not HAS_ORIGINAL_MAIN, reason="Full dependencies not available"
)
def test_full_run_text_pipeline_sync(mock_text_service):
    """Test full DataFog run_text_pipeline_sync with mocked text service."""
    datafog = FullDataFog(text_service=mock_text_service)

    mock_text_service.batch_annotate_text_sync.return_value = [
        {"PERSON": ["Jeff Bezos"]}
    ]

    result = datafog.run_text_pipeline_sync(["Jeff Bezos steps down as Amazon CEO"])

    mock_text_service.batch_annotate_text_sync.assert_called_once_with(
        ["Jeff Bezos steps down as Amazon CEO"]
    )
    assert result == [{"PERSON": ["Jeff Bezos"]}]


def test_lean_datafog_detect():
    """Test lean DataFog detect method."""
    datafog = DataFog()

    test_text = "Contact john@example.com or call (555) 123-4567"
    result = datafog.detect(test_text)

    assert isinstance(result, dict)
    # Should detect email and phone
    assert "EMAIL" in result
    assert "PHONE" in result


def test_lean_datafog_process():
    """Test lean DataFog process method."""
    datafog = DataFog()

    test_text = "Contact john@example.com or call (555) 123-4567"

    # Test without anonymization
    result = datafog.process(test_text, anonymize=False)
    assert result["original"] == test_text
    assert "findings" in result
    assert "anonymized" not in result

    # Test with anonymization
    result = datafog.process(test_text, anonymize=True, method="redact")
    assert result["original"] == test_text
    assert "findings" in result
    assert "anonymized" in result
    assert result["anonymized"] != test_text


@pytest.mark.skipif(
    not HAS_FULL_DEPS or not HAS_ORIGINAL_MAIN, reason="Full dependencies not available"
)
@pytest.mark.parametrize(
    "operation, hash_type, expected_pattern",
    [
        (
            OperationType.REDACT,
            None,
            r"\[REDACTED\] tries one more time to save his \$56 billion pay package",
        ),
        (
            OperationType.REPLACE,
            None,
            r"\[PERSON(_[A-F0-9]+)?\] tries one more time to save his \$56 billion pay package",
        ),
        (
            OperationType.HASH,
            HashType.MD5,
            r"([a-f0-9]{32}) tries one more time to save his \$56 billion pay package",
        ),
        (
            OperationType.HASH,
            HashType.SHA256,
            r"([a-f0-9]{64}) tries one more time to save his \$56 billion pay package",
        ),
        (
            OperationType.HASH,
            HashType.SHA3_256,
            r"([a-f0-9]{64}) tries one more time to save his \$56 billion pay package",
        ),
    ],
)
def test_full_run_text_pipeline_anonymization(
    mock_text_service, operation, hash_type, expected_pattern
):
    """Test full DataFog anonymization with mocked services."""
    logging.basicConfig(level=logging.INFO)
    datafog = FullDataFog(
        text_service=mock_text_service,
        operations=[OperationType.SCAN, operation],
        hash_type=hash_type,
        anonymizer_type=operation,
    )
    mock_text_service.batch_annotate_text_sync.return_value = [
        [
            AnnotationResult(
                start=0,
                end=9,
                entity_type="PERSON",
                text="Elon Musk",
                score=0.9,
                recognition_metadata={"confidence": "high"},
            )
        ]
    ]

    result = datafog.run_text_pipeline_sync(
        ["Elon Musk tries one more time to save his $56 billion pay package"]
    )

    logging.info(f"Result: {result}")
    assert len(result) == 1, "Expected a single result"
    assert re.match(
        expected_pattern, result[0]
    ), f"Result {result[0]!r} does not match pattern {expected_pattern!r}"

    if operation == AnonymizerType.HASH:
        hashed_part = result[0].split()[0]
        if hash_type == HashType.MD5:
            assert len(hashed_part) == 32
        elif hash_type in [HashType.SHA256, HashType.SHA3_256]:
            assert len(hashed_part) == 64
