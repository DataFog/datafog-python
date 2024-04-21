# Description: Define the data models for the PII Detection Workflow

from typing import Any, List, Optional, Tuple

import en_spacy_pii_fast
import requests
from pydantic import BaseModel, HttpUrl


class PIIDetectPipelineModel(BaseModel):
    nlp: Any = None

    def load_model(self):
        if self.nlp is None:
            self.nlp = en_spacy_pii_fast.load()  # Load only when needed
        return self.nlp

    class Config:
        arbitrary_types_allowed = True


class PIIDetectRequest(BaseModel):
    url: Optional[HttpUrl] = None
    language: str = "en"
    instructions: Optional[str] = None
    run_text_extraction: bool = True
    extracted_text: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.run_text_extraction and self.url:
            self.extracted_text = TextExtractor(url=self.url).extract_text()

    @property
    def text(self) -> str:
        return self.extracted_text

    class Config:
        arbitrary_types_allowed = True


class PIIDetectResponse(BaseModel):
    text: str
    entities: List[Tuple[str, str]]


class PIIDetectWorkflow(BaseModel):
    request: PIIDetectRequest
    model: PIIDetectPipelineModel = PIIDetectPipelineModel()

    def process_request(self):
        self.model.load_model()  # Load the model explicitly when needed
        doc = self.model.nlp(self.request.text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        return entities

    def run(self):
        entities = self.process_request()
        response = PIIDetectResponse(text=self.request.text, entities=entities)
        return response

    class Config:
        arbitrary_types_allowed = True


# Ingest file with TextExtractor return Document == PIIDetectRequest
## define TextExtractor
class TextExtractor:
    def __init__(self, text: str = None, url: HttpUrl = None):
        self.text = text
        self.url = url

    def extract_text(self) -> str:
        if self.url:
            response = requests.get(self.url)
            return response.text
        else:
            return self.text
