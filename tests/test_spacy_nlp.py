# tests/test_spacy_nlp.py
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from datafog.models.spacy_nlp import AnnotationResult, SpacyAnnotator


@patch("datafog.models.spacy_nlp.spacy.load")
def test_annotate_text_basic(mock_spacy_load):
    """
    Test that annotate_text correctly processes text and returns AnnotationResult objects.
    """
    # Arrange: Mock the spaCy NLP object and its return value
    mock_nlp = MagicMock()
    mock_doc = MagicMock()

    # Simulate entities found by spaCy
    mock_ent1 = MagicMock()
    mock_ent1.start_char = 0
    mock_ent1.end_char = 4
    mock_ent1.label_ = "PERSON"

    mock_ent2 = MagicMock()
    mock_ent2.start_char = 11
    mock_ent2.end_char = 17
    mock_ent2.label_ = "LOCATION"  # Use valid EntityTypes member

    mock_doc.ents = [mock_ent1, mock_ent2]
    mock_nlp.return_value = mock_doc  # nlp(text) returns the mock_doc
    mock_spacy_load.return_value = mock_nlp  # spacy.load() returns the mock_nlp

    # Instantiate the annotator (doesn't load model immediately)
    annotator = SpacyAnnotator()

    # Act: Call the method under test
    test_text = "John lives in London."
    results = annotator.annotate_text(test_text)

    # Assert:
    # Check that spacy.load was called (implicitly tests load_model)
    mock_spacy_load.assert_called_once_with(annotator.model_name)
    # Check that the nlp object was called with the text
    mock_nlp.assert_called_once()
    # Check the number of results
    assert len(results) == 2

    # Check the details of the first result
    assert isinstance(results[0], AnnotationResult)
    assert results[0].start == 0
    assert results[0].end == 4
    assert results[0].entity_type == "PERSON"
    assert isinstance(results[0].score, float)

    # Check the details of the second result
    assert isinstance(results[1], AnnotationResult)
    assert results[1].start == 11
    assert results[1].end == 17
    assert results[1].entity_type == "LOCATION"  # Assert for LOCATION
    assert isinstance(results[1].score, float)


# Example of testing other branches (e.g., model already loaded)
@patch("datafog.models.spacy_nlp.spacy.load")
def test_annotate_text_model_already_loaded(mock_spacy_load):
    """
    Test that annotate_text doesn't reload the model if already loaded.
    """
    # Arrange
    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_doc.ents = []  # No entities for simplicity
    mock_nlp.return_value = mock_doc
    mock_spacy_load.return_value = mock_nlp

    annotator = SpacyAnnotator()
    annotator.nlp = mock_nlp  # Pre-set the nlp attribute

    # Act
    annotator.annotate_text("Some text.")

    # Assert
    mock_spacy_load.assert_not_called()  # Should not be called again
    mock_nlp.assert_called_once_with("Some text.")
