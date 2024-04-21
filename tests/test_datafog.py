import pytest

from datafog import DataFog

sotu_url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"


@pytest.fixture
def datafog_instance():
    """Creates a DataFog instance for testing, using the SOTU URL."""
    return DataFog(source_url=sotu_url)


def test_sotu_text_extraction(datafog_instance):
    """Validates the text extraction process from the SOTU address."""
    extracted_text = datafog_instance.get_text()

    assert "America" in extracted_text
    assert "future" in extracted_text
    assert "government" in extracted_text


def test_sotu_pii_processing(datafog_instance):
    """Validates the PII processing from the SOTU address."""
    processed_output = datafog_instance.process_text()

    assert "America" in processed_output
    assert "future" in processed_output
    assert "government" in processed_output


#
