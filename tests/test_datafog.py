# test_datafog.py
import pytest
import requests

from datafog import DataFog


@pytest.fixture
def datafog():
    return DataFog()

def test_upload_file(datafog):
    uploaded_file="tests/files/input_files/agi-builder-meetup.pdf"
    result = datafog.upload_file(uploaded_file_path=uploaded_file)
    file_text = result[uploaded_file.split('/')[-1]]  # Extract the text using the file name as key
    assert "Cloudflare" in file_text  # confirms that OCR is not on 
    assert "SF" in file_text
    assert "Laurie" in file_text
    assert "BentoML" in file_text
    assert "Llama-Index" not in file_text
    assert "LlamaIndex" in file_text
    assert "LangChain" not in file_text


# def test_call_with_redact(datafog):
#     url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"
#     privacy_operation = "redact"

#     result = datafog(url, privacy_operation)

#     assert "[REDACTED]" in result
#     assert "Joe Biden" not in result


# def test_call_with_annotate(datafog):
#     file_path = "sotu_2023.txt"
#     url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"
#     file_content = requests.get(url).text
#     with open(file_path, "w") as file:
#         file.write(file_content)
#     privacy_operation = "annotate"

#     result = datafog(str(file_path), privacy_operation)

#     assert "[ORG]" in result
#     assert "Joe Biden" not in result


# def test_call_with_unsupported_input_type(datafog):
#     input_source = 123  # Invalid input type
#     privacy_operation = "redact"

#     with pytest.raises(ValueError, match="Unsupported input source type"):
#         datafog(input_source, privacy_operation)


# def test_call_with_unsupported_privacy_operation(datafog):
#     url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"
#     privacy_operation = "invalid_operation"

#     with pytest.raises(
#         ValueError, match=f"Unsupported privacy operation: {privacy_operation}"
#     ):
#         datafog(url, privacy_operation)
