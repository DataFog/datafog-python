import unittest
from PIL import Image
import pytest
from PIL import Image
from datafog import PipelineOperationType, DonutImageProcessor

# class TestDonutImageProcessor(unittest.TestCase):
#     def setUp(self):
#         self.processor = DonutImageProcessor(operation_type=PipelineOperationType.PARSE_IMAGE)
#         with open("/Users/sidmohan/Desktop/v3.0.0/datafog-python/src/datafog/test-invoice.png", "rb") as image_file:
#             self.image_data = image_file.read()

#     def test_parse_image(self):
#         image = DonutImageProcessor.read_image(self.image_data)
#         result = self.processor.parse_image(image)
#         self.assertIsInstance(result, dict)
#         self.assertIn('MEDICAL BILLING INVOICE', [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist])
#         self.assertIn('12245', [item['price']['unitprice'] for sublist in result.values() if isinstance(sublist, list) for item in sublist if 'unitprice' in item['price']])
#         self.assertIn('Full Check Up', [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist])
#         self.assertIn('Ear & Throat Examination', [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist])

# if __name__ == '__main__':
#     unittest.main()



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
    assert 'MEDICAL BILLING INVOICE' in [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist]
    assert '12245' in [item['price']['unitprice'] for sublist in result.values() if isinstance(sublist, list) for item in sublist if 'unitprice' in item['price']]
    assert 'Full Check Up' in [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist]
    assert 'Ear & Throat Examination' in [item['nm'] for sublist in result.values() if isinstance(sublist, list) for item in sublist]
