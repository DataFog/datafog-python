"""Retirement notices do not require installed OCR/Spark/model dependencies."""

import asyncio
import importlib
import os
import subprocess
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from datafog._legacy_retirement import LegacySurfaceWarning
from datafog.processing.image_processing.donut_processor import DonutProcessor
from datafog.processing.spark_processing import pyspark_udfs
from datafog.services.image_service import ImageService
from datafog.services.spark_service import SparkService


@pytest.mark.parametrize("surface", ["OCR", "Spark"])
def test_optional_service_notice_precedes_dependencies(monkeypatch, surface):
    def unexpected_import(*args):
        pytest.fail("Optional dependency loading must follow the retirement notice")

    monkeypatch.setattr(importlib, "import_module", unexpected_import)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LegacySurfaceWarning)
        with pytest.raises(
            LegacySurfaceWarning,
            match=f"{surface} support is deprecated in 4.9 and will be removed in 5.0",
        ):
            (ImageService if surface == "OCR" else SparkService)()


def test_spark_missing_dependency_error_is_preserved(monkeypatch):
    def unavailable(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", unavailable)
    with (
        pytest.warns(LegacySurfaceWarning, match="final 4.x release"),
        pytest.raises(ImportError, match=r"datafog\[distributed\]"),
    ):
        SparkService()


@pytest.mark.parametrize("factory", [False, True])
def test_spark_udf_paths_warn_before_dependency_loading(monkeypatch, factory):
    dependencies = Mock(side_effect=ImportError("optional dependency unavailable"))
    monkeypatch.setattr(pyspark_udfs, "ensure_installed", dependencies)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LegacySurfaceWarning)
        with pytest.raises(LegacySurfaceWarning, match="Spark.*removed in 5.0"):
            if factory:
                pyspark_udfs.broadcast_pii_annotator_udf()
            else:
                pyspark_udfs.pii_annotator("hello", None)
    dependencies.assert_not_called()


def test_spark_udf_output_is_preserved(monkeypatch):
    monkeypatch.setattr(pyspark_udfs, "ensure_installed", lambda _: None)
    nlp = Mock(
        return_value=SimpleNamespace(ents=[SimpleNamespace(label_="PER", text="Jane")])
    )
    with pytest.warns(LegacySurfaceWarning):
        assert pyspark_udfs.pii_annotator("Jane", SimpleNamespace(value=nlp)) == [
            [],
            [],
            [],
            [],
            ["Jane"],
        ]


def test_donut_mock_output_is_preserved(monkeypatch):
    from datafog.processing.image_processing import donut_processor

    monkeypatch.setattr(donut_processor, "IN_TEST_ENV", True)
    monkeypatch.setattr(donut_processor, "DONUT_TESTING_ENABLED", False)
    with pytest.warns(LegacySurfaceWarning):
        processor = DonutProcessor()
    with pytest.warns(LegacySurfaceWarning, match="final 4.x release"):
        assert asyncio.run(processor.extract_text_from_image(object())) == (
            '{"text": "Mock OCR text for testing"}'
        )


def test_direct_tesseract_processor_warns_and_preserves_output(monkeypatch):
    # Stub optional dependencies even when they are absent from the test environment.
    tesseract = SimpleNamespace(image_to_string=Mock(return_value="OCR text"))
    monkeypatch.setitem(sys.modules, "pytesseract", tesseract)
    monkeypatch.setitem(
        sys.modules, "PIL", SimpleNamespace(Image=SimpleNamespace(Image=object))
    )
    module_name = "datafog.processing.image_processing.pytesseract_processor"
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    processor_module = importlib.import_module(module_name)
    try:
        with pytest.warns(LegacySurfaceWarning, match="OCR.*removed in 5.0"):
            assert (
                asyncio.run(
                    processor_module.PytesseractProcessor().extract_text_from_image(
                        object()
                    )
                )
                == "OCR text"
            )
    finally:
        sys.modules.pop(module_name, None)


def test_ocr_warning_as_error_is_not_converted_to_processing_result(monkeypatch):
    with pytest.warns(LegacySurfaceWarning):
        service = ImageService()
    # Simulate a warning from a nested public processor after outer warning handling.
    monkeypatch.setattr(
        "datafog.services.image_service.warn_legacy_surface", lambda _: None
    )
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(Image=object))
    service.downloader.download_image = AsyncMock(
        side_effect=LegacySurfaceWarning("nested notice")
    )
    with pytest.raises(LegacySurfaceWarning, match="nested notice"):
        asyncio.run(service.ocr_extract(["https://example.test/image.png"]))


def test_ocr_pipeline_warns_before_loading_service(monkeypatch):
    from datafog.main import DataFog

    datafog = DataFog()
    service = Mock()
    monkeypatch.setattr("datafog.services.image_service.ImageService", service)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LegacySurfaceWarning)
        with pytest.raises(LegacySurfaceWarning):
            asyncio.run(datafog.run_ocr_pipeline([]))
    service.assert_not_called()


def test_core_and_optional_module_imports_are_quiet_and_lightweight():
    script = """
import importlib.abc
import sys
import warnings

blocked = {"PIL", "pytesseract", "pyspark", "torch", "transformers", "spacy", "aiohttp", "numpy"}
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in blocked:
            raise AssertionError("Unexpected optional import: " + fullname)
sys.meta_path.insert(0, BlockOptional())
with warnings.catch_warnings(record=True) as notices:
    warnings.simplefilter("always")
    import datafog
    from datafog.services.image_service import ImageService
    from datafog.services.spark_service import SparkService
    from datafog.processing.image_processing.donut_processor import DonutProcessor
    from datafog.processing.spark_processing import pyspark_udfs
    result = datafog.scan("jane@example.com", engine="regex")
    assert result.entities
    from datafog._legacy_retirement import LegacySurfaceWarning
    assert not [n for n in notices if issubclass(n.category, LegacySurfaceWarning)]
assert not (blocked & set(sys.modules))
"""
    env = dict(
        os.environ,
        PYTHONPATH=str(Path.cwd()),
        DATAFOG_NO_TELEMETRY="1",
        DO_NOT_TRACK="1",
    )
    subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "module_name",
    [
        "datafog.services.image_service",
        "datafog.processing.image_processing.image_downloader",
    ],
)
def test_direct_image_download_warns_before_optional_import(module_name):
    module = importlib.import_module(module_name)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LegacySurfaceWarning)
        with pytest.raises(LegacySurfaceWarning, match="OCR.*removed in 5.0"):
            asyncio.run(
                module.ImageDownloader().download_image("https://example.test/a.png")
            )


def test_image_cli_warns_before_running_pipeline(monkeypatch):
    pytest.importorskip("typer")
    from datafog import client

    datafog = Mock()
    monkeypatch.setattr(client, "DataFog", datafog)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LegacySurfaceWarning)
        with pytest.raises(LegacySurfaceWarning, match="OCR.*removed in 5.0"):
            client.scan_image(["image.png"], "scan")
    datafog.assert_not_called()


def test_image_cli_does_not_swallow_nested_retirement_warning(monkeypatch):
    pytest.importorskip("typer")
    from datafog import client

    monkeypatch.setattr(client, "warn_legacy_surface", lambda _: None)
    pipeline = AsyncMock(side_effect=LegacySurfaceWarning("nested notice"))
    monkeypatch.setattr(
        client, "DataFog", Mock(return_value=SimpleNamespace(run_ocr_pipeline=pipeline))
    )
    with pytest.raises(LegacySurfaceWarning, match="nested notice"):
        client.scan_image(["image.png"], "scan")


@pytest.mark.parametrize("image_argument", [False, True])
def test_image_cli_notice_visible_under_default_python_filters(image_argument):
    pytest.importorskip("typer")
    # A fresh interpreter avoids pytest's warning filters and cached warning sites.
    # Do not enable warnings here: the normal interpreter policy must show this.
    script = """
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from typer.testing import CliRunner
from datafog import client

pipeline = AsyncMock(return_value=["OCR text"])
client.DataFog = Mock(return_value=SimpleNamespace(run_ocr_pipeline=pipeline))
args = ["scan-image"]
if sys.argv[1] == "True":
    args.append("image.png")
result = CliRunner().invoke(client.app, args)
assert "deprecated in 4.9 and will be removed in 5.0" in result.stderr, result.output
assert "final 4.x release" in result.stderr, result.output
if sys.argv[1] == "True":
    assert result.exit_code == 0, result.output
    assert "OCR Pipeline Results: ['OCR text']" in result.stdout
    pipeline.assert_awaited_once_with(image_urls=["image.png"])
else:
    assert result.exit_code == 1, result.output
    assert "No image URLs or file paths provided" in result.stdout
    pipeline.assert_not_awaited()
"""
    env = dict(
        os.environ,
        PYTHONPATH=str(Path.cwd()),
        DATAFOG_NO_TELEMETRY="1",
        DO_NOT_TRACK="1",
    )
    env.pop("PYTHONWARNINGS", None)
    subprocess.run(
        [sys.executable, "-c", script, str(image_argument)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
