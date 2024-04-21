from pydantic import HttpUrl

from .models import (
    PIIDetectPipelineModel,
    PIIDetectRequest,
    PIIDetectWorkflow,
    TextExtractor,
)


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

    def process_text(self):
        if not self.pii_detection:
            return {"message": "PII detection is not enabled."}

        request = PIIDetectRequest(url=self.source_url)
        workflow = PIIDetectWorkflow(request=request, model=self.model)
        return workflow.run()

    def get_text(self):
        # Fetch and return text without PII processing
        extractor = TextExtractor(url=self.source_url)
        return extractor.extract_text()
