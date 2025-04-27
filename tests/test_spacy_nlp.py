# tests/test_spacy_nlp.py
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

# Import the function and cache we want to test directly
from datafog.models.spacy_nlp import (
    _SPACY_MODEL_CACHE,
    AnnotationResult,
    SpacyAnnotator,
    _get_spacy_model,
)


@pytest.fixture(autouse=True)
def clear_spacy_cache_before_test():
    """Fixture to clear the spaCy model cache before each test."""
    _SPACY_MODEL_CACHE.clear()
    yield  # Test runs here
    _SPACY_MODEL_CACHE.clear()  # Clean up after test too, just in case


@patch("datafog.models.spacy_nlp.spacy.load")
def test_annotate_text_basic(mock_spacy_load):
    """
    Test that annotate_text correctly processes a batch of texts using nlp.pipe
    and returns a list of lists of AnnotationResult objects.
    """
    # Arrange: Mock the spaCy NLP object and its pipe method
    mock_nlp = MagicMock()
    mock_doc1 = MagicMock()
    mock_doc2 = MagicMock()

    # Simulate entities for the first text
    mock_ent1_doc1 = MagicMock(start_char=0, end_char=4, label_="PERSON")
    mock_ent2_doc1 = MagicMock(start_char=11, end_char=17, label_="LOCATION")
    mock_doc1.ents = [mock_ent1_doc1, mock_ent2_doc1]

    # Simulate entities for the second text
    mock_ent1_doc2 = MagicMock(start_char=0, end_char=5, label_="PERSON")
    mock_ent2_doc2 = MagicMock(start_char=16, end_char=22, label_="ORG")
    mock_doc2.ents = [mock_ent1_doc2, mock_ent2_doc2]

    # Mock the return value of nlp.pipe to be an iterator of our mock docs
    mock_nlp.pipe.return_value = iter([mock_doc1, mock_doc2])
    mock_spacy_load.return_value = mock_nlp  # spacy.load() returns the mock_nlp

    # Instantiate the annotator
    annotator = SpacyAnnotator()

    # Act: Call the method under test with a list of texts
    test_texts = ["John lives in London.", "Alice works at Google."]
    results = annotator.annotate_text(test_texts)

    # Assert:
    # Check that spacy.load was called (implicitly tests load_model)
    mock_spacy_load.assert_called_once_with(annotator.model_name)
    # Check that nlp.pipe was called with the texts and default args
    mock_nlp.pipe.assert_called_once_with(test_texts, batch_size=50, n_process=-1)

    # Check the structure of the results (list of lists)
    assert isinstance(results, list)
    assert len(results) == 2  # One list of results for each input text
    assert isinstance(results[0], list)
    assert isinstance(results[1], list)

    # --- Check results for the first text --- #
    assert len(results[0]) == 2
    # First entity
    assert isinstance(results[0][0], AnnotationResult)
    assert results[0][0].start == 0
    assert results[0][0].end == 4
    assert results[0][0].entity_type == "PERSON"
    assert isinstance(results[0][0].score, float)
    # Second entity
    assert isinstance(results[0][1], AnnotationResult)
    assert results[0][1].start == 11
    assert results[0][1].end == 17
    assert results[0][1].entity_type == "LOCATION"
    assert isinstance(results[0][1].score, float)

    # --- Check results for the second text --- #
    assert len(results[1]) == 2
    # First entity
    assert isinstance(results[1][0], AnnotationResult)
    assert results[1][0].start == 0
    assert results[1][0].end == 5
    assert results[1][0].entity_type == "PERSON"
    assert isinstance(results[1][0].score, float)
    # Second entity
    assert isinstance(results[1][1], AnnotationResult)
    assert results[1][1].start == 16
    assert results[1][1].end == 22
    # Expect UNKNOWN because 'ORG' is not in EntityTypes enum (validator replaces it)
    assert results[1][1].entity_type == "UNKNOWN"
    assert isinstance(results[1][1].score, float)


# Example of testing other branches (e.g., model already loaded)
@patch("datafog.models.spacy_nlp.spacy.load")
def test_annotate_text_model_already_loaded(mock_spacy_load):
    """
    Test that annotate_text doesn't reload the model if already loaded
    and still calls nlp.pipe correctly.
    """
    # Arrange
    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_doc.ents = []  # No entities for simplicity
    mock_nlp.pipe.return_value = iter([mock_doc])  # nlp.pipe returns iterator
    mock_spacy_load.return_value = mock_nlp  # This shouldn't be called if pre-set

    annotator = SpacyAnnotator()
    annotator.nlp = mock_nlp  # Pre-set the nlp attribute

    # Act
    test_texts = ["Some text."]
    results = annotator.annotate_text(test_texts)

    # Assert
    mock_spacy_load.assert_not_called()  # Should not be called again
    mock_nlp.pipe.assert_called_once_with(test_texts, batch_size=50, n_process=-1)
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], list)
    assert len(results[0]) == 0  # No entities expected


# --- Tests for _get_spacy_model Caching --- #


@patch("datafog.models.spacy_nlp.spacy.util.is_package", return_value=True)
@patch("datafog.models.spacy_nlp.spacy.load")
def test_get_spacy_model_cache_hit(mock_spacy_load, mock_is_package):
    """Verify that the model is loaded only once for the same name."""
    # Arrange: Create mock models
    mock_nlp_1 = MagicMock(name="model_lg")
    mock_spacy_load.return_value = mock_nlp_1
    model_name = "en_core_web_lg"

    # Act: Call twice with the same model name
    nlp_obj1 = _get_spacy_model(model_name)
    nlp_obj2 = _get_spacy_model(model_name)

    # Assert: spacy.load called only once, returned objects are the same instance
    mock_is_package.assert_called_once_with(
        model_name
    )  # is_package check happens first
    mock_spacy_load.assert_called_once_with(model_name)
    assert nlp_obj1 is nlp_obj2
    assert model_name in _SPACY_MODEL_CACHE
    assert _SPACY_MODEL_CACHE[model_name] is nlp_obj1


@patch("datafog.models.spacy_nlp.spacy.util.is_package", return_value=True)
@patch("datafog.models.spacy_nlp.spacy.load")
def test_get_spacy_model_cache_miss_different_models(mock_spacy_load, mock_is_package):
    """Verify that different models are loaded and cached separately."""
    # Arrange: Mock different return values for spacy.load
    mock_nlp_lg = MagicMock(name="model_lg")
    mock_nlp_sm = MagicMock(name="model_sm")
    mock_spacy_load.side_effect = [mock_nlp_lg, mock_nlp_sm]
    model_name_lg = "en_core_web_lg"
    model_name_sm = "en_core_web_sm"

    # Act: Call with different model names
    nlp_obj_lg = _get_spacy_model(model_name_lg)
    nlp_obj_sm = _get_spacy_model(model_name_sm)

    # Assert: spacy.load called for each model, objects are different
    assert mock_is_package.call_count == 2
    assert mock_spacy_load.call_count == 2
    mock_spacy_load.assert_any_call(model_name_lg)
    mock_spacy_load.assert_any_call(model_name_sm)
    assert nlp_obj_lg is not nlp_obj_sm
    assert nlp_obj_lg is mock_nlp_lg
    assert nlp_obj_sm is mock_nlp_sm
    assert model_name_lg in _SPACY_MODEL_CACHE
    assert model_name_sm in _SPACY_MODEL_CACHE
    assert _SPACY_MODEL_CACHE[model_name_lg] is nlp_obj_lg
    assert _SPACY_MODEL_CACHE[model_name_sm] is nlp_obj_sm


@patch("datafog.models.spacy_nlp.spacy.cli.download")
@patch("datafog.models.spacy_nlp.spacy.load")
@patch("datafog.models.spacy_nlp.spacy.util.is_package", return_value=False)
def test_get_spacy_model_triggers_download(
    mock_is_package, mock_spacy_load, mock_download
):
    """Verify that spacy.cli.download is called if model package is not found."""
    # Arrange
    mock_nlp = MagicMock(name="downloaded_model")
    mock_spacy_load.return_value = mock_nlp
    model_name = "en_new_model"

    # Act
    nlp_obj = _get_spacy_model(model_name)

    # Assert
    mock_is_package.assert_called_once_with(model_name)
    mock_download.assert_called_once_with(model_name)
    mock_spacy_load.assert_called_once_with(model_name)
    assert nlp_obj is mock_nlp
    assert model_name in _SPACY_MODEL_CACHE
