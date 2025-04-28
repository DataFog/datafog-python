# tests/test_spark_service.py
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# DO NOT import datafog.services.spark_service at the top level


@pytest.mark.skip(
    reason="Skipping due to complex mocking interactions with dependencies. "
    "Needs revisit when SparkService has real functionality."
)
def test_spark_service_handles_pyspark_import_error(capsys):
    """
    Test that SparkService handles ImportError for pyspark gracefully during import
    and prints the expected message, isolating it from dependency import errors.
    """
    # Ensure the module under test and its dependency are not cached
    if "datafog.services.spark_service" in sys.modules:
        del sys.modules["datafog.services.spark_service"]
    if "datafog.processing.spark_processing.pyspark_udfs" in sys.modules:
        del sys.modules["datafog.processing.spark_processing.pyspark_udfs"]

    # Store original state
    original_modules = sys.modules.copy()

    # Modules to remove/mock
    modules_to_patch = {}
    # Remove pyspark
    modules_to_patch["pyspark"] = None
    modules_to_patch["pyspark.sql"] = None  # Also remove submodule just in case
    # Mock the problematic dependency
    modules_to_patch["datafog.processing.spark_processing.pyspark_udfs"] = MagicMock()

    # Use patch.dict to modify sys.modules for this context
    with patch.dict(
        sys.modules, modules_to_patch, clear=False
    ):  # clear=False, just overlay
        try:
            # Attempt to import the module *within* the patch context
            # The import of spark_service itself should trigger its try/except
            # The import *within* spark_service for pyspark_udfs should get the MagicMock
            import datafog.services.spark_service as spark_service

            # Check if the warning message was printed (stdout)
            captured = capsys.readouterr()
            expected_message = (
                "PySpark not found. Please install it with the [spark] extra"
            )
            assert expected_message in captured.out

            # Check stderr for the traceback from spark_service's except block
            assert (
                "ImportError" in captured.err or "ModuleNotFoundError" in captured.err
            )
            assert "pyspark" in captured.err

            # Verify that the placeholder is set in the imported module
            assert spark_service.SparkSession is None

            # Verify dependency was mocked (optional, but good practice)
            assert isinstance(spark_service.pyspark_udfs, MagicMock)

        finally:
            # Strict restoration of original modules is important
            sys.modules.clear()
            sys.modules.update(original_modules)
            # Re-delete the target module and dependency to ensure clean state
            if "datafog.services.spark_service" in sys.modules:
                del sys.modules["datafog.services.spark_service"]
            if "datafog.processing.spark_processing.pyspark_udfs" in sys.modules:
                del sys.modules["datafog.processing.spark_processing.pyspark_udfs"]


# Add placeholder for actual SparkService tests later if needed
# class TestSparkServiceFunctionality:
#     @pytest.mark.skipif(sys.modules.get("pyspark") is None, reason="pyspark not installed")
#     def test_spark_functionality(self):
#         # Add tests for actual service methods here
#         pass
