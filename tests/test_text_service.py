from unittest.mock import Mock, patch

import pytest

from datafog.services.text_service import TextService


@pytest.fixture
def mock_annotator():
    mock = Mock()
    mock.annotate.return_value = {"PER": ["John Doe"], "ORG": ["Acme Inc"]}
    return mock


@pytest.fixture
def text_service(mock_annotator):
    with patch(
        "datafog.services.text_service.SpacyPIIAnnotator.create",
        return_value=mock_annotator,
    ):
        return TextService(text_chunk_length=10)


def test_init(text_service):
    assert text_service.text_chunk_length == 10


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
