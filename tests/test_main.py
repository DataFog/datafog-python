# unittest below in comments
import pytest
from datafog import DataFog, PipelineOperationType

@pytest.fixture
def datafog():
    return DataFog(operation_type=PipelineOperationType.PARSE_IMAGE, image_processor=True, text_pii_annotation=True)

def test_process_text(datafog):
    text = "John Smith lives in Wonderland."
    entities = datafog.process_text(text)
    assert len(entities) > 0
    assert ('John Smith', 'PER') in entities
    assert ('Wonderland', 'LOC') in entities

def test_process_image(datafog):
    sample_image_path = "tests/test-invoice.png"
    with open(sample_image_path, "rb") as image_file:
        image_data = image_file.read()
    result = datafog.process_image(image_data)
    assert isinstance(result, dict)
    names = [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist]
    unit_prices = [item['price']['unitprice'] for sublist in result.values() if isinstance(sublist, list) for item in sublist if 'unitprice' in item['price']]
    assert 'MEDICAL BILLING INVOICE' in names
    assert '12245' in unit_prices
    assert 'Full Check Up' in names
    assert 'Ear & Throat Examination' in names

def test_annotate_pii_in_images(datafog):
    sample_image_path = "tests/test-invoice.png"
    with open(sample_image_path, "rb") as image_file:
        image_data = image_file.read()
    annotated_result = datafog.annotate_pii_in_images(image_data)

    # Check if 'entities' is added and contains expected PII entity types.
    for sublist in annotated_result.values():
        if isinstance(sublist, list):
            for item in sublist:
                if 'nm' in item:
                    print("Item Name:", item['nm'], "Entities:", item.get('entities'))
                    assert 'entities' in item
                    # Check for at least one 'ORG' or 'LOC' entity in each item

