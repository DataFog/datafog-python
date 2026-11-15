"""Regression contracts for the November 2026 entrypoint review."""

import asyncio
import hashlib
import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import datafog
from datafog.agent import create_guardrail
from datafog.client import app
from datafog.config import OperationType, get_config
from datafog.main import DataFog, TextPIIAnnotator
from datafog.models.annotator import AnnotationResult, AnnotatorRequest
from datafog.models.anonymizer import Anonymizer, AnonymizerType, HashType
from datafog.models.common import EntityTypes

EMAIL = "jane@" "example.com"


@pytest.mark.asyncio
async def test_decorator_awaits_and_filters():
    @create_guardrail()
    async def answer():
        await asyncio.sleep(0)
        return EMAIL

    assert EMAIL not in await answer()


@pytest.mark.parametrize("output", [[EMAIL], {"text": EMAIL}, None, 1])
def test_guarded_non_strings_rejected(output):
    @create_guardrail()
    def answer():
        return output

    with pytest.raises(TypeError, match="must return a string"):
        answer()


@pytest.mark.parametrize(
    "operation", [OperationType.REDACT, OperationType.REPLACE, OperationType.HASH]
)
def test_anonymizing_operations_imply_scan(operation):
    service = DataFog(operations=[operation])
    assert EMAIL not in service.run_text_pipeline_sync([EMAIL])[0]
    assert EMAIL not in service.process_text(EMAIL)


@pytest.mark.parametrize("algorithm", list(HashType))
def test_hash_algorithm_honored_across_api_and_cli(algorithm):
    digest = hashlib.new(algorithm.value, EMAIL.encode()).hexdigest()
    assert (
        digest
        in DataFog(hash_type=algorithm).process(EMAIL, anonymize=True, method="hash")[
            "anonymized"
        ]
    )
    assert (
        digest
        in datafog.process(
            EMAIL, anonymize=True, method="hash", hash_type=algorithm.value
        )["anonymized"]
    )
    result = CliRunner().invoke(
        app, ["hash-text", EMAIL, "--hash-type", algorithm.value]
    )
    assert result.exit_code == 0, result.output
    assert digest in result.stdout


def test_keyed_hash_public_facades():
    import hmac

    key = b"k" * 32
    digest = hmac.new(key, EMAIL.encode(), "sha256").hexdigest()
    assert digest in datafog.redact(EMAIL, strategy="hash", hash_key=key).redacted_text
    assert digest in datafog.anonymize_text(EMAIL, method="hash", hash_key=key)
    assert (
        digest
        in datafog.process(EMAIL, anonymize=True, method="hash", hash_key=key)[
            "anonymized"
        ]
    )


@pytest.mark.parametrize(
    "factory", [lambda: datafog.process, lambda: DataFog().process]
)
def test_bad_method_rejected(factory):
    with pytest.raises(ValueError, match="method"):
        factory()(EMAIL, anonymize=True, method="bogus")


def test_legacy_detection_uses_core():
    text = "card 6011111111111117 ip 2001:db8::1"
    assert {item["type"] for item in datafog.detect(text)} >= {
        "CREDIT_CARD",
        "IP_ADDRESS",
    }
    assert "6011111111111117" not in datafog.process(text, anonymize=True)["anonymized"]
    assert "IP_ADDRESS" in TextPIIAnnotator().run(text)
    assert "JWT" in datafog.get_supported_entities()


def test_annotation_defaults_and_labels():
    assert AnnotatorRequest(text="x", language="en").score_threshold is None
    for label in ["SSN", "ORG", "GPE", "IP_ADDRESS"]:
        assert (
            AnnotationResult(start=0, end=1, entity_type=label).entity_type != "UNKNOWN"
        )


def test_enum_filter_and_date_replacement():
    annotation = AnnotationResult(
        start=0, end=len(EMAIL), entity_type=EntityTypes.EMAIL
    )
    assert (
        Anonymizer(anonymizer_type="redact", entities=[EntityTypes.EMAIL])
        .anonymize(EMAIL, [annotation])
        .anonymized_text
        == "[REDACTED]"
    )
    date = AnnotationResult(start=0, end=10, entity_type="DATE")
    assert (
        Anonymizer().anonymize("2024-01-02", [date]).anonymized_text
        == "[REDACTED_DATE]"
    )


@pytest.mark.parametrize("strategy", list(AnonymizerType))
def test_legacy_overlaps_never_leave_partial_value(strategy):
    text = "abcdefghij"
    spans = [
        AnnotationResult(start=0, end=6, entity_type="EMAIL"),
        AnnotationResult(start=4, end=10, entity_type="SSN"),
    ]
    result = Anonymizer(anonymizer_type=strategy).anonymize(text, spans)
    assert "ghij" not in result.anonymized_text
    assert len(result.anonymized_entities) == 1
    assert result.anonymized_entities[0]["original"] == text


def test_cli_hides_key_and_handles_bad_operation():
    config = get_config()
    old_key = config.api_key
    try:
        config.api_key = "private-test-key"
        result = CliRunner().invoke(app, ["show-config"])
        assert result.exit_code == 0
        assert "private-test-key" not in result.stdout
        assert "REDACTED" in result.stdout
    finally:
        config.api_key = old_key
    result = CliRunner().invoke(app, ["scan-text", EMAIL, "--operations", "bogus"])
    assert result.exit_code == 2
    assert "operations must use" in result.output
    assert "Traceback" not in result.output


def test_import_and_cli_preserve_logger_level():
    logger = logging.getLogger("datafog_logger")
    old = logger.level
    try:
        logger.setLevel(logging.ERROR)
        import importlib

        import datafog.main

        importlib.reload(datafog.main)
        assert logger.level == logging.ERROR
    finally:
        logger.setLevel(old)


def test_spark_real_spacy_labels_and_oversize(monkeypatch):
    from datafog.processing.spark_processing import pyspark_udfs as spark

    monkeypatch.setattr(spark, "ensure_installed", lambda _: None)

    def nlp(text):
        return SimpleNamespace(
            ents=[
                SimpleNamespace(label_="PERSON", text="Ann"),
                SimpleNamespace(label_="ORG", text="Acme"),
            ]
        )

    with pytest.warns(FutureWarning):
        result = spark.pii_annotator("Ann at Acme", SimpleNamespace(value=nlp))
    assert result[spark.PII_ANNOTATION_LABELS.index("PER")] == ["Ann"]
    assert result[spark.PII_ANNOTATION_LABELS.index("ORG")] == ["Acme"]
    with pytest.warns(FutureWarning), pytest.raises(ValueError, match="maximum"):
        spark.pii_annotator(
            "x" * (spark.MAXIMAL_STRING_SIZE + 1), SimpleNamespace(value=nlp)
        )


def _version_selector():
    path = Path(__file__).parents[1] / "scripts/release_version.py"
    spec = importlib.util.spec_from_file_location("release_version", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.select_version


@pytest.mark.parametrize(
    "current, kind, override",
    [
        ("4.9.0a2", "alpha", None),
        ("4.11.0", "beta", None),
        ("4.12.0", "stable", "4.10.0"),
    ],
)
def test_release_rejects_stale_bases(current, kind, override):
    with pytest.raises(ValueError, match="newer than"):
        _version_selector()(current, kind, [], "4.11.0", override)


def test_release_version_positive_and_duplicate_paths():
    select = _version_selector()
    assert select("4.12.0", "alpha", ["v4.12.0a1"], "4.11.0") == "4.12.0a2"
    assert select("4.12.0", "stable", [], "4.11.0") == "4.12.0"
    with pytest.raises(ValueError, match="already exists"):
        select("4.12.0", "stable", ["v4.12.0"], "4.11.0")


def test_release_skips_published_prereleases_without_tags():
    select = _version_selector()
    assert select("4.12.0", "alpha", [], "4.11.0", published=["4.12.0a1"]) == "4.12.0a2"
