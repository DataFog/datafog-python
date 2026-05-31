import os
import subprocess
import sys
from pathlib import Path


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


def test_no_torch_import_when_donut_disabled():
    """Test that torch is not imported when use_donut is False"""
    _run_isolated_python(
        """
import sys
from datafog.services.image_service import ImageService

_ = ImageService(use_donut=False, use_tesseract=True)

assert "torch" not in sys.modules
assert "transformers" not in sys.modules
"""
    )


def test_lazy_import_mechanism():
    """Test the lazy import mechanism for DonutProcessor"""
    # This test verifies that the DonutProcessor class has been refactored
    # to use lazy imports. We don't need to actually test the imports themselves,
    # just that the structure is correct.

    _run_isolated_python(
        """
import sys
from datafog.processing.image_processing.donut_processor import DonutProcessor

processor = DonutProcessor()

assert "torch" not in sys.modules
assert "transformers" not in sys.modules
assert hasattr(processor, "extract_text_from_image")
assert not hasattr(processor, "ensure_installed")
"""
    )
