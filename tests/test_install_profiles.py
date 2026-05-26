import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATAFOG_INSTALL_PROFILE"),
    reason="install profile smoke tests run only in profile-specific CI jobs",
)


def test_install_profile_import_surface() -> None:
    profile = os.environ["DATAFOG_INSTALL_PROFILE"]

    if profile == "core":
        import datafog

        assert datafog.scan("Email jane@example.com").entities
        assert datafog.redact("Email jane@example.com").redacted_text
    elif profile == "cli":
        import click  # noqa: F401

        from datafog.client import app

        assert app is not None
    elif profile == "nlp":
        import click  # noqa: F401
        import spacy  # noqa: F401

        from datafog.models.spacy_nlp import SpacyAnnotator
        from datafog.processing.text_processing.spacy_pii_annotator import (
            SpacyPIIAnnotator,
        )

        assert SpacyAnnotator is not None
        assert SpacyPIIAnnotator is not None
    elif profile == "nlp-advanced":
        import gliner  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401

        from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator

        assert GLiNERAnnotator is not None
    elif profile == "ocr":
        import numpy  # noqa: F401
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401

        from datafog.processing.image_processing.donut_processor import DonutProcessor
        from datafog.processing.image_processing.pytesseract_processor import (
            PytesseractProcessor,
        )
        from datafog.services.image_service import ImageService

        assert DonutProcessor is not None
        assert ImageService is not None
        assert PytesseractProcessor is not None
        if os.environ.get("DATAFOG_REQUIRE_TESSERACT"):
            assert pytesseract.get_tesseract_version()
    elif profile == "distributed":
        from datafog.processing.spark_processing import pyspark_udfs
        from datafog.services.spark_service import SparkService

        pyspark_udfs.ensure_installed("pyspark")
        assert SparkService is not None
    elif profile == "web":
        import aiohttp  # noqa: F401
        import certifi  # noqa: F401
        import fastapi  # noqa: F401
        import requests  # noqa: F401
    else:
        raise AssertionError(f"unknown DATAFOG_INSTALL_PROFILE: {profile}")
