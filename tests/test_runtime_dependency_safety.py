import importlib
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest


def _run_isolated_python(script: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path.cwd())
    env["DATAFOG_NO_TELEMETRY"] = "1"
    env["DO_NOT_TRACK"] = "1"
    return subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )


def test_runtime_code_does_not_install_packages() -> None:
    blocked_snippets = [
        "subprocess.check_call",
        "subprocess.run",
        '"-m", "pip"',
        '"pip", "install"',
        "'pip', 'install'",
    ]
    offenders = []

    for path in Path("datafog").rglob("*.py"):
        source = path.read_text()
        for snippet in blocked_snippets:
            if snippet in source:
                offenders.append(f"{path}: {snippet}")

    assert offenders == []


def test_ocr_and_spark_public_services_do_not_require_optional_imports() -> None:
    _run_isolated_python(
        """
import importlib.abc
import sys

blocked = {
    "aiohttp",
    "certifi",
    "PIL",
    "pyspark",
    "pytesseract",
    "torch",
    "transformers",
}

class BlockOptionalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise AssertionError(f"optional dependency imported: {fullname}")
        return None

sys.meta_path.insert(0, BlockOptionalImports())

import datafog
from datafog.services import ImageService, SparkService, TextService

assert datafog.scan("Email jane@example.com").entities
assert ImageService is not None
assert SparkService is not None
assert TextService is not None
assert datafog.ImageService is ImageService
assert datafog.SparkService is SparkService
"""
    )


def test_spacy_pii_missing_model_requires_explicit_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSpacy:
        @staticmethod
        def load(_model_name):
            raise OSError("model not installed")

    monkeypatch.setitem(sys.modules, "spacy", FakeSpacy())

    from datafog.processing.text_processing.spacy_pii_annotator import \
        SpacyPIIAnnotator

    with pytest.raises(ImportError, match="Download it explicitly"):
        SpacyPIIAnnotator.create()


def test_spacy_engine_missing_model_surfaces_download_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSpacy:
        @staticmethod
        def load(_model_name):
            raise OSError("model not installed")

    monkeypatch.setitem(sys.modules, "spacy", FakeSpacy())

    from datafog import engine
    from datafog.exceptions import EngineNotAvailable

    engine._get_spacy_annotator.cache_clear()
    try:
        with pytest.raises(EngineNotAvailable, match="Download it explicitly"):
            engine.scan("Jane Doe", engine="spacy")
    finally:
        engine._get_spacy_annotator.cache_clear()


def test_spacy_engine_missing_module_surfaces_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datafog import engine
    from datafog.exceptions import EngineNotAvailable

    module_name = "datafog.processing.text_processing.spacy_pii_annotator"
    monkeypatch.setitem(sys.modules, module_name, None)

    engine._get_spacy_annotator.cache_clear()
    try:
        with pytest.raises(EngineNotAvailable, match="spacy_pii_annotator"):
            engine.scan("Jane Doe", engine="spacy")
    finally:
        engine._get_spacy_annotator.cache_clear()


def test_gliner_engine_missing_module_surfaces_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datafog import engine
    from datafog.exceptions import EngineNotAvailable

    module_name = "datafog.processing.text_processing.gliner_annotator"
    monkeypatch.setitem(sys.modules, module_name, None)

    engine._get_gliner_annotator.cache_clear()
    try:
        with pytest.raises(EngineNotAvailable, match="gliner_annotator"):
            engine.scan("Jane Doe", engine="gliner")
    finally:
        engine._get_gliner_annotator.cache_clear()


def test_spacy_helper_does_not_require_rich(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "datafog.models.spacy_nlp"
    monkeypatch.delitem(sys.modules, module_name, raising=False)

    fake_spacy = types.ModuleType("spacy")
    fake_spacy.load = lambda _model_name: None
    fake_spacy.cli = types.SimpleNamespace(download=lambda _model_name: None)
    fake_spacy.util = types.SimpleNamespace(get_installed_models=lambda: [])
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)

    module = importlib.import_module(module_name)

    assert module.SpacyAnnotator is not None


def test_spark_missing_dependency_requires_explicit_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datafog.services import spark_service

    def missing_module(_package_name):
        raise ImportError("missing")

    monkeypatch.setattr(spark_service.importlib, "import_module", missing_module)

    service = spark_service.SparkService.__new__(spark_service.SparkService)
    with pytest.raises(ImportError, match=r"datafog\[distributed\]"):
        service.ensure_installed("pyspark")


def test_spark_udf_missing_dependency_requires_explicit_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datafog.processing.spark_processing import pyspark_udfs

    def missing_module(_package_name):
        raise ImportError("missing")

    monkeypatch.setattr(pyspark_udfs.importlib, "import_module", missing_module)

    with pytest.raises(ImportError, match=r"datafog\[nlp\]"):
        pyspark_udfs.ensure_installed("spacy")


@pytest.mark.asyncio
async def test_donut_missing_dependency_requires_explicit_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datafog.processing.image_processing import donut_processor

    monkeypatch.setattr(donut_processor, "IN_TEST_ENV", False)
    monkeypatch.setitem(sys.modules, "torch", None)

    processor = donut_processor.DonutProcessor()

    with pytest.raises(ImportError, match=r"datafog\[nlp-advanced,ocr\]"):
        await processor.extract_text_from_image(object())
