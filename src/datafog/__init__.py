from pydantic import HttpUrl

from .models import (
    PIIDetectPipelineModel,
    PIIDetectRequest,
    PIIDetectWorkflow,
    TextExtractor,
)
from .image_processors import DonutImageProcessor


class DataFog:
    def __init__(self, source_url: HttpUrl = None, pii_detection: bool = False):
        self.pii_detection = pii_detection
        self.source_url = source_url
        if pii_detection:
            self.model = (
                PIIDetectPipelineModel()
            )  # Load the NLP model for PII detection
        else:
            self.model = None


    def detect_pii(self):
        if not self.pii_detection:
            return {"message": "PII detection is not enabled."}

        request = PIIDetectRequest(url=self.source_url)
        workflow = PIIDetectWorkflow(request=request, model=self.model)
        return workflow.run()


    def get_text(self):
        # Fetch and return text without PII processing
        extractor = TextExtractor(url=self.source_url)
        return extractor.extract_text()
    


    def process_image(self, image_path: str, operation_type: str, question: str = None):
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
            image = DonutImageProcessor.read_image(image_bytes)
        except Exception as e:
            return {"error": f"Failed to process image: {e}"}

        processor = DonutImageProcessor(operation_type)
        if operation_type == "read":
            output = processor.classify_image(image)
        elif operation_type == "parse":
            output = processor.parse_image(image)
        elif operation_type == "vqa":
            if question is None:
                question = "what is shown in this image?"
            output = processor.question_image(image, question)
        else:
            return {"error": "Invalid operation type specified."}

        return output
