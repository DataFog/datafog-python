import pytest

from datafog.models.annotator import AnnotationResult, AnnotatorMetadata
from datafog.models.anonymizer import (
    AnonymizationResult,
    Anonymizer,
    AnonymizerType,
    HashType,
)
from datafog.models.common import EntityTypes


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


def test_anonymizer_replace(sample_text, sample_annotations):
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REPLACE)
    result = anonymizer.anonymize(sample_text, sample_annotations)

    assert isinstance(result, AnonymizationResult)
    assert result.anonymized_text != sample_text
    assert len(result.anonymized_entities) == 3

    for replacement in result.anonymized_entities:
        assert replacement["original"] in sample_text
        assert replacement["replacement"] not in sample_text
        assert replacement["entity_type"] in EntityTypes.__members__

        expected_prefix = f"[{replacement['entity_type']}_"
        assert replacement["replacement"].startswith(expected_prefix)
        assert replacement["replacement"].endswith("]")


def test_anonymizer_redact(sample_text, sample_annotations):
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REDACT)
    result = anonymizer.anonymize(sample_text, sample_annotations)

    assert result.anonymized_text != sample_text
    assert len(result.anonymized_entities) == 3

    for replacement in result.anonymized_entities:
        assert replacement["original"] in sample_text
        assert replacement["replacement"] == "[REDACTED]"


@pytest.mark.parametrize(
    "hash_type", [HashType.MD5, HashType.SHA256, HashType.SHA3_256]
)
def test_anonymizer_hash(sample_text, sample_annotations, hash_type):
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.HASH, hash_type=hash_type)
    result = anonymizer.anonymize(sample_text, sample_annotations)

    assert result.anonymized_text != sample_text
    assert len(result.anonymized_entities) == 3

    for replacement in result.anonymized_entities:
        assert replacement["original"] in sample_text
        assert replacement["replacement"] not in sample_text
        # assert len(replacement["replacement"]) == len(replacement["original"])
        # Check hash type-specific properties
        if hash_type == HashType.MD5:
            assert len(replacement["replacement"]) == 32
        elif hash_type in [HashType.SHA256, HashType.SHA3_256]:
            assert len(replacement["replacement"]) == 64


def test_anonymizer_with_specific_entities(sample_text, sample_annotations):
    anonymizer = Anonymizer(
        anonymizer_type=AnonymizerType.REPLACE, entities=[EntityTypes.ORGANIZATION]
    )
    result = anonymizer.anonymize(sample_text, sample_annotations)

    assert result.anonymized_text != sample_text
    assert len(result.anonymized_entities) == 1
    assert result.anonymized_entities[0]["entity_type"] == EntityTypes.ORGANIZATION
    assert result.anonymized_entities[0]["original"] == "DigiCorp Incorporated "
    assert result.anonymized_entities[0]["replacement"].startswith("[ORGANIZATION_")
    assert result.anonymized_entities[0]["replacement"].endswith("]")

    assert "Jeff Smith" in result.anonymized_text
    assert "Paris" in result.anonymized_text
    assert "DigiCorp Incorporated" not in result.anonymized_text


def test_anonymizer_invalid_type():
    with pytest.raises(ValueError):
        Anonymizer(anonymizer_type="invalid_type")


@pytest.mark.parametrize("anonymizer_type", list(AnonymizerType))
def test_all_anonymizer_types(anonymizer_type, sample_text, sample_annotations):
    anonymizer = Anonymizer(anonymizer_type=anonymizer_type)
    result = anonymizer.anonymize(sample_text, sample_annotations)

    assert isinstance(result, AnonymizationResult)
    assert result.anonymized_text != sample_text
    assert len(result.anonymized_entities) == 3
