from unittest.mock import Mock, patch

import pytest

from datafog.services.text_service import TextService


@pytest.fixture
def mock_annotator():
    mock = Mock()
    mock.annotate.return_value = {"PER": ["John Doe"], "ORG": ["Acme Inc"]}
    return mock


@pytest.fixture
def mock_regex_annotator():
    mock = Mock()
    mock.annotate.return_value = {
        "EMAIL": ["john@example.com"],
        "PHONE": ["555-555-5555"],
    }
    return mock


@pytest.fixture
def text_service(mock_annotator, mock_regex_annotator):
    # Configure regex annotator to return empty results so auto mode falls back to spaCy
    # This ensures backward compatibility with existing tests while using 'auto' mode
    mock_regex_annotator.annotate.return_value = {
        key: []
        for key in ["EMAIL", "PHONE", "SSN", "CREDIT_CARD", "IP_ADDRESS", "DOB", "ZIP"]
    }

    with patch(
        "datafog.services.text_service.SpacyPIIAnnotator.create",
        return_value=mock_annotator,
    ):
        with patch(
            "datafog.services.text_service.RegexAnnotator",
            return_value=mock_regex_annotator,
        ):
            # Use 'auto' engine to match production default, but regex will find nothing
            # so it will always fall back to spaCy, maintaining test compatibility
            return TextService(text_chunk_length=10, engine="auto")


@pytest.fixture
def text_service_with_engine(mock_annotator, mock_regex_annotator):
    def _create_service(engine="auto"):
        with patch(
            "datafog.services.text_service.SpacyPIIAnnotator.create",
            return_value=mock_annotator,
        ):
            with patch(
                "datafog.services.text_service.RegexAnnotator",
                return_value=mock_regex_annotator,
            ):
                return TextService(text_chunk_length=10, engine=engine)

    return _create_service


def test_init(text_service):
    assert text_service.text_chunk_length == 10


def test_init_with_default_engine(text_service):
    assert text_service.text_chunk_length == 10
    # We're using 'auto' in our fixture to match production default
    assert text_service.engine == "auto"


def test_init_with_custom_engine(text_service_with_engine):
    service = text_service_with_engine(engine="regex")
    assert service.engine == "regex"

    service = text_service_with_engine(engine="spacy")
    assert service.engine == "spacy"

    service = text_service_with_engine(engine="auto")
    assert service.engine == "auto"


def test_init_with_invalid_engine():
    with pytest.raises(AssertionError, match="Invalid engine"):
        with patch(
            "datafog.services.text_service.SpacyPIIAnnotator.create",
        ):
            with patch(
                "datafog.services.text_service.RegexAnnotator",
            ):
                TextService(engine="invalid")


def test_chunk_text(text_service):
    text = "This is a test sentence for chunking."
    chunks = text_service._chunk_text(text)
    assert len(chunks) == 4
    assert chunks == ["This is a ", "test sente", "nce for ch", "unking."]


def test_combine_annotations(text_service):
    annotations = [
        {"PER": ["John"], "ORG": ["Acme"]},
        {"PER": ["Doe"], "LOC": ["New York"]},
    ]
    combined = text_service._combine_annotations(annotations)
    assert combined == {"PER": ["John", "Doe"], "ORG": ["Acme"], "LOC": ["New York"]}


def test_annotate_text_sync(text_service):
    result = text_service.annotate_text_sync("John Doe works at Acme Inc")
    assert result == {
        "PER": ["John Doe", "John Doe", "John Doe"],
        "ORG": ["Acme Inc", "Acme Inc", "Acme Inc"],
    }


def test_batch_annotate_text_sync(text_service):
    texts = ["John Doe", "Acme Inc"]
    result = text_service.batch_annotate_text_sync(texts)
    assert result == {
        "John Doe": {"PER": ["John Doe"], "ORG": ["Acme Inc"]},
        "Acme Inc": {"PER": ["John Doe"], "ORG": ["Acme Inc"]},
    }


@pytest.mark.asyncio
async def test_annotate_text_async(text_service):
    result = await text_service.annotate_text_async("John Doe works at Acme Inc")
    assert result == {
        "PER": ["John Doe", "John Doe", "John Doe"],
        "ORG": ["Acme Inc", "Acme Inc", "Acme Inc"],
    }


@pytest.mark.asyncio
async def test_batch_annotate_text_async(text_service):
    texts = ["John Doe", "Acme Inc"]
    result = await text_service.batch_annotate_text_async(texts)
    assert result == {
        "John Doe": {"PER": ["John Doe"], "ORG": ["Acme Inc"]},
        "Acme Inc": {"PER": ["John Doe"], "ORG": ["Acme Inc"]},
    }


def test_long_text_chunking(text_service):
    long_text = "John Doe works at Acme Inc. Jane Smith is from New York City."
    result = text_service.annotate_text_sync(long_text)
    expected_count = len(text_service._chunk_text(long_text))
    assert result == {
        "PER": ["John Doe"] * expected_count,
        "ORG": ["Acme Inc"] * expected_count,
    }


@pytest.mark.asyncio
async def test_long_text_chunking_async(text_service):
    long_text = "John Doe works at Acme Inc. Jane Smith is from New York City."
    result = await text_service.annotate_text_async(long_text)
    expected_count = len(text_service._chunk_text(long_text))
    assert result == {
        "PER": ["John Doe"] * expected_count,
        "ORG": ["Acme Inc"] * expected_count,
    }


def test_empty_string(text_service):
    result = text_service.annotate_text_sync("")
    assert result == {}


def test_short_string(text_service):
    result = text_service.annotate_text_sync("Short")
    assert result == {"PER": ["John Doe"], "ORG": ["Acme Inc"]}


def test_special_characters(text_service):
    result = text_service.annotate_text_sync("John@Doe.com works at Acme-Inc!!!")
    expected_count = len(text_service._chunk_text("John@Doe.com works at Acme-Inc!!!"))
    assert result == {
        "PER": ["John Doe"] * expected_count,
        "ORG": ["Acme Inc"] * expected_count,
    }


def test_regex_engine(text_service_with_engine, mock_regex_annotator):
    service = text_service_with_engine(engine="regex")
    # Override chunk length to avoid multiple calls
    service.text_chunk_length = 1000
    result = service.annotate_text_sync("john@example.com")

    # Should only call the regex annotator
    assert mock_regex_annotator.annotate.called
    assert not service.spacy_annotator.annotate.called
    assert result == {"EMAIL": ["john@example.com"], "PHONE": ["555-555-5555"]}


def test_spacy_engine(text_service_with_engine, mock_annotator):
    service = text_service_with_engine(engine="spacy")
    # Override chunk length to avoid multiple calls
    service.text_chunk_length = 1000
    result = service.annotate_text_sync("John Doe works at Acme Inc")

    # Should only call the spaCy annotator
    assert mock_annotator.annotate.called
    assert not service.regex_annotator.annotate.called
    assert result == {"PER": ["John Doe"], "ORG": ["Acme Inc"]}


def test_auto_engine_with_regex_results(
    text_service_with_engine, mock_regex_annotator, mock_annotator
):
    # Configure regex annotator to return results
    mock_regex_annotator.annotate.return_value = {"EMAIL": ["john@example.com"]}

    service = text_service_with_engine(engine="auto")
    # Override chunk length to avoid multiple calls
    service.text_chunk_length = 1000
    result = service.annotate_text_sync("john@example.com")

    # Should call regex annotator but not spaCy
    assert mock_regex_annotator.annotate.called
    assert not mock_annotator.annotate.called

    assert result == {"EMAIL": ["john@example.com"]}


def test_auto_engine_with_fallback(
    text_service_with_engine, mock_regex_annotator, mock_annotator
):
    # Configure regex annotator to return empty results
    mock_regex_annotator.annotate.return_value = {"EMAIL": [], "PHONE": []}

    service = text_service_with_engine(engine="auto")
    # Override chunk length to avoid multiple calls
    service.text_chunk_length = 1000
    result = service.annotate_text_sync("John Doe works at Acme Inc")

    # Should call both annotators
    assert mock_regex_annotator.annotate.called
    assert mock_annotator.annotate.called

    assert result == {"PER": ["John Doe"], "ORG": ["Acme Inc"]}
