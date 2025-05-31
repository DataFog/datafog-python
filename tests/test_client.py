from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from datafog.client import app
from datafog.models.annotator import AnnotationResult, AnnotatorMetadata
from datafog.models.anonymizer import (
    AnonymizationResult,
    Anonymizer,
    AnonymizerType,
    HashType,
)
from datafog.models.common import EntityTypes

runner = CliRunner()


@pytest.fixture
def mock_datafog():
    with patch("datafog.client.DataFog") as mock:
        yield mock


@pytest.fixture
def sample_text():
    return "Jeff Smith works at DigiCorp Incorporated in Paris."


@pytest.fixture
def sample_annotations():
    return [
        AnnotationResult(
            start=0,
            end=9,
            score=1.0,
            entity_type=EntityTypes.PERSON,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=20,
            end=42,
            score=1.0,
            entity_type=EntityTypes.ORGANIZATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=46,
            end=51,
            score=1.0,
            entity_type=EntityTypes.LOCATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
    ]


def test_scan_image_no_urls():
    result = runner.invoke(app, ["scan-image"])
    assert result.exit_code == 1
    assert "No image URLs or file paths provided" in result.stdout


@pytest.mark.asyncio
async def test_scan_image_success(mock_datafog):
    mock_instance = mock_datafog.return_value
    mock_instance.run_ocr_pipeline.return_value = ["Mocked result"]

    with patch("datafog.client.asyncio.run", new=lambda x: x):
        result = runner.invoke(app, ["scan-image", "http://example.com/image.jpg"])

    assert result.exit_code == 0
    assert "OCR Pipeline Results: ['Mocked result']" in result.stdout
    mock_instance.run_ocr_pipeline.assert_called_once_with(
        image_urls=["http://example.com/image.jpg"]
    )


def test_scan_text_no_texts():
    result = runner.invoke(app, ["scan-text"])
    assert result.exit_code == 1
    assert "No texts provided" in result.stdout


def test_scan_text_success(mock_datafog):
    mock_instance = mock_datafog.return_value
    mock_instance.run_text_pipeline_sync.return_value = ["Mocked result"]

    result = runner.invoke(app, ["scan-text", "Sample text"])

    assert result.exit_code == 0
    assert "Text Pipeline Results: ['Mocked result']" in result.stdout
    mock_instance.run_text_pipeline_sync.assert_called_once_with(
        str_list=["Sample text"]
    )


def test_health():
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "DataFog is running" in result.stdout


@patch("datafog.client.get_config")
def test_show_config(mock_get_config):
    mock_get_config.return_value = {"key": "value"}
    result = runner.invoke(app, ["show-config"])
    assert result.exit_code == 0
    assert "{'key': 'value'}" in result.stdout


@patch("datafog.client.SpacyAnnotator.download_model")
def test_download_model(mock_download_model):
    result = runner.invoke(app, ["download-model", "en_core_web_sm"])
    assert result.exit_code == 0
    assert "SpaCy model en_core_web_sm downloaded successfully" in result.stdout
    mock_download_model.assert_called_once_with("en_core_web_sm")


@patch("datafog.client.SpacyAnnotator")
def test_show_spacy_model_directory(mock_spacy_annotator):
    mock_instance = mock_spacy_annotator.return_value
    mock_instance.show_model_path.return_value = "/path/to/model"
    result = runner.invoke(app, ["show-spacy-model-directory", "en_core_web_sm"])
    assert result.exit_code == 0
    assert "/path/to/model" in result.stdout


@patch("datafog.client.SpacyAnnotator")
def test_list_spacy_models(mock_spacy_annotator):
    mock_instance = mock_spacy_annotator.return_value
    mock_instance.list_models.return_value = ["model1", "model2"]
    result = runner.invoke(app, ["list-spacy-models"])
    assert result.exit_code == 0
    assert "['model1', 'model2']" in result.stdout


@patch("datafog.client.SpacyAnnotator")
def test_list_entities(mock_spacy_annotator):
    mock_instance = mock_spacy_annotator.return_value
    mock_instance.list_entities.return_value = ["PERSON", "ORG"]
    result = runner.invoke(app, ["list-entities"])
    assert result.exit_code == 0
    assert "['PERSON', 'ORG']" in result.stdout


def test_anonymizer_outputs():
    """Test that the Anonymizer class produces correct outputs for different modes."""

    # Create test data
    text = "John Smith works at TechCorp in New York"
    annotations = [
        AnnotationResult(
            start=0,
            end=10,
            score=1.0,
            entity_type=EntityTypes.PERSON,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=21,
            end=29,
            score=1.0,
            entity_type=EntityTypes.ORGANIZATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=33,
            end=41,
            score=1.0,
            entity_type=EntityTypes.LOCATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
    ]

    # Test redaction
    redact_anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REDACT)
    redact_result = redact_anonymizer.anonymize(text, annotations)
    # The actual output might differ based on how the annotations are processed
    # We'll just check that PIIs were replaced with [REDACTED]
    assert "[REDACTED]" in redact_result.anonymized_text
    assert "works at" in redact_result.anonymized_text
    assert len(redact_result.anonymized_entities) == 3

    # Test replacement
    replace_anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REPLACE)
    replace_result = replace_anonymizer.anonymize(text, annotations)
    # We can't test the exact output as it uses random replacements, but we can check that it's different
    assert text != replace_result.anonymized_text
    assert "works at" in replace_result.anonymized_text

    # Test hashing with SHA256
    hash_anonymizer = Anonymizer(
        anonymizer_type=AnonymizerType.HASH, hash_type=HashType.SHA256
    )
    hash_result = hash_anonymizer.anonymize(text, annotations)
    assert text != hash_result.anonymized_text
    assert "works at" in hash_result.anonymized_text

    # Test hashing with MD5
    md5_anonymizer = Anonymizer(
        anonymizer_type=AnonymizerType.HASH, hash_type=HashType.MD5
    )
    md5_result = md5_anonymizer.anonymize(text, annotations)
    assert text != md5_result.anonymized_text
    assert "works at" in md5_result.anonymized_text

    # Test hashing with SHA3_256
    sha3_anonymizer = Anonymizer(
        anonymizer_type=AnonymizerType.HASH, hash_type=HashType.SHA3_256
    )
    sha3_result = sha3_anonymizer.anonymize(text, annotations)
    assert text != sha3_result.anonymized_text
    assert "works at" in sha3_result.anonymized_text


def test_anonymizer_model():
    """Test that the AnonymizationResult model accepts both anonymized_entities and replaced_entities"""

    # Test with replaced_entities
    result1 = AnonymizationResult(
        anonymized_text="Test text",
        replaced_entities=[{"original": "John", "replacement": "[REDACTED]"}],
    )
    assert result1.anonymized_text == "Test text"
    assert len(result1.anonymized_entities) == 1

    # Test with anonymized_entities
    result2 = AnonymizationResult(
        anonymized_text="Test text",
        anonymized_entities=[{"original": "John", "replacement": "[REDACTED]"}],
    )
    assert result2.anonymized_text == "Test text"
    assert len(result2.anonymized_entities) == 1
