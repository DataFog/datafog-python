from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from datafog.client import app
from datafog.models.annotator import AnnotationResult, AnnotatorMetadata
from datafog.models.anonymizer import AnonymizationResult, AnonymizerType, HashType
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


@pytest.mark.asyncio
async def test_scan_text_success(mock_datafog):
    mock_instance = mock_datafog.return_value
    mock_instance.run_text_pipeline.return_value = ["Mocked result"]

    with patch("datafog.client.asyncio.run", new=lambda x: x):
        result = runner.invoke(app, ["scan-text", "Sample text"])

    assert result.exit_code == 0
    assert "Text Pipeline Results: ['Mocked result']" in result.stdout
    mock_instance.run_text_pipeline.assert_called_once_with(str_list=["Sample text"])


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
    assert "Model en_core_web_sm downloaded" in result.stdout
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


@patch("datafog.client.SpacyAnnotator")
@patch("datafog.client.Anonymizer")
def test_redact_text(mock_anonymizer, mock_spacy_annotator, sample_annotations):
    mock_annotator = mock_spacy_annotator.return_value
    mock_anonymizer_instance = mock_anonymizer.return_value

    sample_text = "John Doe works at Acme Corp"
    sample_annotations = [
        AnnotationResult(
            start=0,
            end=8,
            score=1.0,
            entity_type=EntityTypes.PERSON,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=18,
            end=27,
            score=1.0,
            entity_type=EntityTypes.ORGANIZATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
    ]
    mock_annotator.annotate_text.return_value = sample_annotations

    mock_anonymizer_instance.anonymize.return_value = AnonymizationResult(
        anonymized_text="[REDACTED] works at [REDACTED]", anonymized_entities=[]
    )

    result = runner.invoke(app, ["redact-text", sample_text])

    assert result.exit_code == 0
    assert "[REDACTED] works at [REDACTED]" in result.stdout
    mock_spacy_annotator.assert_called_once()
    mock_anonymizer.assert_called_once_with(anonymizer_type=AnonymizerType.REDACT)
    mock_annotator.annotate_text.assert_called_once_with(sample_text)
    mock_anonymizer_instance.anonymize.assert_called_once_with(
        sample_text, sample_annotations
    )


@patch("datafog.client.SpacyAnnotator")
@patch("datafog.client.Anonymizer")
def test_replace_text(mock_anonymizer, mock_spacy_annotator):
    mock_annotator = mock_spacy_annotator.return_value
    mock_anonymizer_instance = mock_anonymizer.return_value

    sample_text = "John Doe works at Acme Corp"
    sample_annotations = [
        AnnotationResult(
            start=0,
            end=8,
            score=1.0,
            entity_type=EntityTypes.PERSON,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=18,
            end=27,
            score=1.0,
            entity_type=EntityTypes.ORGANIZATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
    ]
    mock_annotator.annotate_text.return_value = sample_annotations

    mock_anonymizer_instance.anonymize.return_value = AnonymizationResult(
        anonymized_text="Jane Smith works at TechCo Inc", anonymized_entities=[]
    )

    result = runner.invoke(app, ["replace-text", sample_text])

    assert result.exit_code == 0
    assert "Jane Smith works at TechCo Inc" in result.stdout
    mock_spacy_annotator.assert_called_once()
    mock_anonymizer.assert_called_once_with(anonymizer_type=AnonymizerType.REPLACE)
    mock_annotator.annotate_text.assert_called_once_with(sample_text)
    mock_anonymizer_instance.anonymize.assert_called_once_with(
        sample_text, sample_annotations
    )


@patch("datafog.client.SpacyAnnotator")
@patch("datafog.client.Anonymizer")
def test_hash_text(mock_anonymizer, mock_spacy_annotator):
    mock_annotator = mock_spacy_annotator.return_value
    mock_anonymizer_instance = mock_anonymizer.return_value

    sample_text = "John Doe works at Acme Corp"
    sample_annotations = [
        AnnotationResult(
            start=0,
            end=8,
            score=1.0,
            entity_type=EntityTypes.PERSON,
            recognition_metadata=AnnotatorMetadata(),
        ),
        AnnotationResult(
            start=18,
            end=27,
            score=1.0,
            entity_type=EntityTypes.ORGANIZATION,
            recognition_metadata=AnnotatorMetadata(),
        ),
    ]
    mock_annotator.annotate_text.return_value = sample_annotations

    mock_anonymizer_instance.anonymize.return_value = AnonymizationResult(
        anonymized_text="5ab5c95f works at 7b23f032", anonymized_entities=[]
    )

    result = runner.invoke(app, ["hash-text", sample_text])

    assert result.exit_code == 0
    assert "5ab5c95f works at 7b23f032" in result.stdout
    mock_spacy_annotator.assert_called_once()
    mock_anonymizer.assert_called_once_with(
        anonymizer_type=AnonymizerType.HASH, hash_type=HashType.SHA256
    )
    mock_annotator.annotate_text.assert_called_once_with(sample_text)
    mock_anonymizer_instance.anonymize.assert_called_once_with(
        sample_text, sample_annotations
    )

    # Test with custom hash type
    result = runner.invoke(app, ["hash-text", sample_text, "--hash-type", "md5"])

    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.stdout}")
    print(f"Exception: {result.exception}")

    assert result.exit_code == 0
    mock_anonymizer.assert_called_with(
        anonymizer_type=AnonymizerType.HASH, hash_type=HashType.MD5
    )
