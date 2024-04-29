import pytest

from datafog import DonutImageProcessor, PipelineOperationType


@pytest.fixture
def processor():
    return DonutImageProcessor(operation_type=PipelineOperationType.PARSE_IMAGE)


def test_parse_image(processor):
    sample_image_path = "tests/test-invoice.png"
    with open(sample_image_path, "rb") as image_file:
        image_data = image_file.read()
    image = DonutImageProcessor.read_image(image_data)
    result = processor.parse_image(image)
    assert isinstance(result, dict)
    assert "MEDICAL BILLING INVOICE" in [
        item["nm"]
        for sublist in result.values()
        if isinstance(sublist, list)
        for item in sublist
    ]
    assert "12245" in [
        item["price"]["unitprice"]
        for sublist in result.values()
        if isinstance(sublist, list)
        for item in sublist
        if "unitprice" in item["price"]
    ]
    assert "Full Check Up" in [
        item["nm"]
        for sublist in result.values()
        if isinstance(sublist, list)
        for item in sublist
    ]
    assert "Ear & Throat Examination" in [
        item["nm"]
        for sublist in result.values()
        if isinstance(sublist, list)
        for item in sublist
    ]
