"""Integration tests for SparkService in local mode."""

import json
import os
import tempfile

import pytest

from datafog.services.spark_service import SparkService


@pytest.fixture(scope="module")
def spark_service():
    """Create a shared SparkService instance for all tests."""
    # Initialize SparkService with explicit local mode
    service = SparkService(master="local[1]")

    yield service

    # Clean up after all tests
    if hasattr(service, "spark") and service.spark is not None:
        service.spark.stop()


@pytest.fixture
def sample_json_data():
    """Create a temporary JSON file with sample data for testing."""
    data = [
        {"name": "John Doe", "email": "john.doe@example.com", "age": 30},
        {"name": "Jane Smith", "email": "jane.smith@example.com", "age": 25},
        {"name": "Bob Johnson", "email": "bob.johnson@example.com", "age": 40},
    ]

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
        temp_file = f.name

    yield temp_file

    # Clean up the temporary file after the test
    if os.path.exists(temp_file):
        os.remove(temp_file)


@pytest.mark.integration
def test_spark_service_initialization(spark_service):
    """Test that SparkService can be initialized in local mode."""
    # Verify that the Spark session was created successfully
    assert spark_service.spark is not None
    assert spark_service.spark.sparkContext.appName == "datafog"
    assert spark_service.spark.sparkContext.master.startswith("local")

    # Verify that the necessary Spark classes are available
    assert spark_service.DataFrame is not None
    assert spark_service.SparkSession is not None
    assert spark_service.udf is not None


@pytest.mark.integration
def test_spark_read_json(spark_service, sample_json_data):
    """Test that SparkService can read JSON data in local mode."""
    # Read the JSON data
    result = spark_service.read_json(sample_json_data)

    # Verify the result
    assert len(result) == 3, f"Expected 3 rows, got {len(result)}"

    # PySpark Row objects have a __contains__ method and can be accessed like dictionaries
    # but they're not actually dictionaries
    assert all(hasattr(item, "name") for item in result), "Missing 'name' field"
    assert all(hasattr(item, "email") for item in result), "Missing 'email' field"
    assert all(hasattr(item, "age") for item in result), "Missing 'age' field"

    # Verify specific values
    names = [item.name for item in result]
    assert "John Doe" in names, f"Expected 'John Doe' in {names}"
    assert "Jane Smith" in names, f"Expected 'Jane Smith' in {names}"
    assert "Bob Johnson" in names, f"Expected 'Bob Johnson' in {names}"
