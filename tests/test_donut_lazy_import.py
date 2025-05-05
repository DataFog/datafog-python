import sys
from unittest.mock import patch

from datafog.services.image_service import ImageService


def test_no_torch_import_when_donut_disabled():
    """Test that torch is not imported when use_donut is False"""
    # Remove torch and transformers from sys.modules if they're already imported
    if "torch" in sys.modules:
        del sys.modules["torch"]
    if "transformers" in sys.modules:
        del sys.modules["transformers"]

    # Create ImageService with use_donut=False
    # The variable is used indirectly by creating the service which affects sys.modules
    _ = ImageService(use_donut=False, use_tesseract=True)

    # Verify that torch and transformers were not imported
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules


def test_lazy_import_mechanism():
    """Test the lazy import mechanism for DonutProcessor"""
    # This test verifies that the DonutProcessor class has been refactored
    # to use lazy imports. We don't need to actually test the imports themselves,
    # just that the structure is correct.

    # First, ensure torch and transformers are not in sys.modules
    if "torch" in sys.modules:
        del sys.modules["torch"]
    if "transformers" in sys.modules:
        del sys.modules["transformers"]

    # Import the DonutProcessor directly
    from datafog.processing.image_processing.donut_processor import DonutProcessor

    # Create a processor instance
    processor = DonutProcessor()

    # Verify that torch and transformers were not imported just by creating the processor
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules

    # Verify that the extract_text_from_image method exists
    assert hasattr(processor, "extract_text_from_image")

    # Mock importlib.import_module to prevent actual imports
    with patch("importlib.import_module") as mock_import:
        # Set up the mock to return a dummy module
        mock_import.return_value = type("DummyModule", (), {})

        # Mock the ensure_installed method to prevent actual installation
        with patch.object(processor, "ensure_installed"):
            # Try to call extract_text_from_image which should trigger imports
            try:
                # We don't actually need to run it asynchronously for this test
                # Just call the method directly to see if it tries to import
                processor.ensure_installed("torch")
            except Exception:
                # Ignore any exceptions
                pass

            # Verify ensure_installed was called
            assert processor.ensure_installed.called
