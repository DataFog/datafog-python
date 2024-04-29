from .donuttransformer import DonutImageProcessor,  PipelineOperationType
from PIL import Image
from .pii_annotation import PIIAnnotationModel, PIIAnnotationRequest, PIIAnnotationPipeline
from typing import Any, List, Optional, Tuple
from enum import Enum




class DataFog:
    """
    A class to process data using the Donut model for image operations and the Spacy model for text operations.

    Attributes:
        operation_type (str): The type of operation to perform ('read', 'parse', 'vqa') for images.
        text_model (PIIAnnotationModel): The model associated with the Spacy model for text operations.
        image_processor (DonutImageProcessor): The processor associated with the Donut model for image operations.

    Methods:
        process_text(text: str) -> list:
            Processes the text for PII entities using the Spacy model.

        process_image(file: bytes) -> dict:
            Processes the image for different operations using the Donut model.

        process_image_with_text(file: bytes, text: str) -> dict:
            Processes the image for different operations using the Donut model and text for PII entities using the Spacy model.
    """
    def __init__(self, operation_type: PipelineOperationType, text_pii_annotation: bool = True, image_processor: bool = False):
        self.text_pii_annotation = text_pii_annotation
        if text_pii_annotation:
            self.text_annotator = PIIAnnotationModel()
        self.image_processor = None
        if image_processor:
            self.image_processor = DonutImageProcessor(operation_type=operation_type)


    def process_text(self, text: str) -> list:
        request = PIIAnnotationRequest(text=text)
        workflow = PIIAnnotationPipeline(request=request, model=self.text_annotator)
        entities = workflow.process_request()
        return entities
    

    def process_image(self, file: bytes) -> dict:
        image = DonutImageProcessor.read_image(file)
        if self.image_processor.operation_type == PipelineOperationType.READ_IMAGE:
            result = self.image_processor.classify_image(image)
        elif self.image_processor.operation_type == PipelineOperationType.PARSE_IMAGE:
            result = self.image_processor.parse_image(image)
        else:
            raise ValueError(f"Unsupported operation type: {self.image_processor.operation_type}")
        return result

    def annotate_pii_in_images(self, file: bytes) -> dict:
        result = self.process_image(file)
        if self.text_pii_annotation:
            # Iterate over the result and annotate PII into a new dictionary
            for key, value in result.items():
                if isinstance(value, list):
                    for item in value:
                        if 'nm' in item:
                            item['entities'] = self.process_text(item['nm'])  # Store entities directly within the item
        return result  # Return the modified result dictionary



