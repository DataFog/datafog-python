import asyncio
import importlib
import sys
import pytest
from unittest.mock import patch

from datafog.services.image_service import ImageService


def test_no_torch_import_when_donut_disabled():
    """Test that torch is not imported when use_donut is False"""
    # Remove torch and transformers from sys.modules if they're already imported
    if 'torch' in sys.modules:
        del sys.modules['torch']
    if 'transformers' in sys.modules:
        del sys.modules['transformers']
    
    # Create ImageService with use_donut=False
    image_service = ImageService(use_donut=False, use_tesseract=True)
    
    # Verify that torch and transformers were not imported
    assert 'torch' not in sys.modules
    assert 'transformers' not in sys.modules


def test_lazy_import_mechanism():
    """Test the lazy import mechanism for DonutProcessor"""
    # This test verifies that the DonutProcessor class has been refactored
    # to use lazy imports. We don't need to actually test the imports themselves,
    # just that the structure is correct.
    
    # Create ImageService with use_donut=True
    image_service = ImageService(use_donut=True, use_tesseract=False)
    
    # Check that the donut_processor was created
    assert image_service.donut_processor is not None
    
    # Verify that the extract_text_from_image method exists
    assert hasattr(image_service.donut_processor, 'extract_text_from_image')
    
    # Mock the imports to verify they're only imported when needed
    with patch('importlib.import_module') as mock_import:
        # Create a new processor to avoid side effects
        from datafog.processing.image_processing.donut_processor import DonutProcessor
        processor = DonutProcessor()
        
        # At this point, torch should not have been imported
        assert 'torch' not in sys.modules
        assert 'transformers' not in sys.modules
        
        # Mock the ensure_installed method to avoid actual installation
        with patch.object(processor, 'ensure_installed'):
            # Call extract_text_from_image with None (it will fail but that's ok)
            try:
                # This will attempt to import torch and transformers
                asyncio.run(processor.extract_text_from_image(None))
            except:
                pass
            
            # Verify that ensure_installed was called for torch and transformers
            assert processor.ensure_installed.call_count >= 1
