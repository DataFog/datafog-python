import os

import polars as pl
import pytest

import datafog
from datafog.presidio import PresidioPolarFog

# import tempfile


@pytest.fixture
def sample_csv_file():
    # Setup: Create a temporary CSV file
    # with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmpfile:
    #     tmpfile.write(
    #         "name,email\nJohn Doe,john.doe@example.com\nJane Doe,jane.doe@example.com"
    #     )
    #     return tmpfile.name
    return "/Users/sidmohan/Desktop/v2.0.0/datafog-python/tests/files/sample.csv"


# test init of PresidioPolarFog
def test_init_presidio_polar_fog():
    presidio = datafog.PresidioPolarFog()
    assert presidio is not None


def test_presidio_call(sample_csv_file):
    presidio = PresidioPolarFog()
    output_file_path = sample_csv_file.rsplit(".", 1)[0] + "_scanned.csv"

    # Action: Process the file
    presidio(sample_csv_file)

    # Assertion: Check the output file exists
    assert os.path.exists(output_file_path), "Output file was not created"

    # Optional: Read the output file and assert content changes
    scrubbed_df = pl.read_csv(output_file_path)
    assert scrubbed_df.shape
    # Teardown: Remove temporary files
    # os.remove(sample_csv_file)
    # os.remove(output_file_path)
