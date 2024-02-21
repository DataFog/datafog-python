import pytest
import requests_mock
from polars import DataFrame

from datafog.pii_tools import presidio  # Adjust the import path as necessary


@pytest.fixture
def presidio_engine():
    return presidio.PresidioEngine()


def test_process_input_http(presidio_engine):
    test_url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"
    test_data = "name,age\nJohn Doe,30\nJane Doe,25"
    with requests_mock.Mocker() as m:
        m.get(test_url, text=test_data)
        df = presidio_engine.process_input(test_url)
    assert isinstance(df, DataFrame)
    assert len(df) >= 1  # Assuming your CSV has two rows of data


def test_process_input_csv_string(presidio_engine):
    test_data = "jerome powell is chair of the federal reserve"
    df = presidio_engine.process_input(test_data)
    assert isinstance(df, DataFrame)


def test_process_input_csv_file(tmp_path, presidio_engine):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.csv"
    p.write_text("name,age\nJohn Doe,30\nJane Doe,25")
    df = presidio_engine.process_input(str(p))
    assert isinstance(df, DataFrame)
    assert len(df) == 2


def test_process_input_non_csv(presidio_engine):
    test_data = "Just a simple string"
    df = presidio_engine.process_input(test_data)
    assert isinstance(df, DataFrame)
    # Check the DataFrame content or structure as needed
