import os
import sys

import requests

from datafog import PresidioEngine as presidio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_piiscan_json_detection():
    # Assuming sample_file already contains the data you want to test
    sample_file = "tests/files/input_files/sample.json"

    # Read the contents of sample_file into original_value
    with open(sample_file, "r") as f:
        original_value = f.read()

    pii_detected = presidio.scan(original_value)

    # write pii_detected to a JSON file called output.json in the same directory as sample_file
    with open(
        "tests/files/output_files/output.json",
        "w",
    ) as f:
        for entity in pii_detected:
            f.write(entity.entity_type)
            f.write("\n")


def test_piiscan_csv_detection():
    # Assuming sample_file already contains the data you want to test
    sample_file = "tests/files/input_files/sample.csv"

    # Read the contents of sample_file into original_value
    with open(sample_file, "r") as f:
        original_value = f.read()

    pii_detected = presidio.scan(original_value)

    # write pii_detected to a JSON file called output.json in the same directory as sample_file
    with open(
        "tests/files/output_files/output.csv",
        "w",
    ) as f:
        for entity in pii_detected:
            f.write(entity.entity_type)
            f.write("\n")


def test_piiscan_txt_detection():
    # Assuming sample_file already contains the data you want to test
    sample_file = "tests/files/input_files/sample.txt"
    # Read the contents of sample_file into original_value
    with open(sample_file, "r") as f:
        original_value = f.read()

    pii_detected = presidio.scan(original_value)

    # write pii_detected to a JSON file called output.json in the same directory as sample_file
    with open(
        "tests/files/output_files/output.txt",
        "w",
    ) as f:
        for entity in pii_detected:
            f.write(entity.entity_type)
            f.write("\n")


def test_piiscan_url_detection():
    # Assuming sample_file already contains the data you want to test
    sample_url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"

    response = requests.get(sample_url)
    original_value = response.text
    pii_detected = presidio.scan(original_value)

    # write pii_detected to a output.md in the same directory as sample_url
    with open(
        "tests/files/output_files/output.md",
        "w",
    ) as f:
        for entity in pii_detected:
            f.write(entity.entity_type)
            f.write("\n")
