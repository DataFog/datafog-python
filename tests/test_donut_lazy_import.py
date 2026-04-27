import sys

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

    # Runtime package installation helpers should not exist on the processor.
    assert not hasattr(processor, "ensure_installed")
