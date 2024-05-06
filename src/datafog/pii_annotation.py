# Description: Define the data models for the PII Detection Workflow

from typing import Any, List, Tuple

import en_spacy_pii_fast
from pydantic import BaseModel, DirectoryPath, FilePath, HttpUrl


class PIIAnnotationModel(BaseModel):
    nlp: Any = None

    def load_model(self):
        if self.nlp is None:
            self.nlp = en_spacy_pii_fast.load()  # Load only when needed
        return self.nlp

    class Config:
        arbitrary_types_allowed = True

    def __fields_set__(self, fields):
        return all(f in fields for f in self.__fields_set__)


class PIIAnnotationRequest(BaseModel):
    text: str = None
    file_path: FilePath = None
    url: HttpUrl = None
    directory_path: DirectoryPath = None

    # add conditional that if none of the fields are filled out, to return an error
    def validate_fields(self):
        if not any([self.text, self.file_path, self.url, self.directory_path]):
            raise ValueError("At least one of the fields must be filled out")
        return True


class PIIAnnotationResponse(BaseModel):
    text: str
    entities: List[Tuple[str, str]]


class PIIAnnotationPipeline(BaseModel):
    request: PIIAnnotationRequest
    model: PIIAnnotationModel = PIIAnnotationModel()

    def process_request(self):
        self.model.load_model()  # Load the model explicitly when needed
        doc = self.model.nlp(self.request.text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        return entities

    def run(self):
        entities = self.process_request()
        response = PIIAnnotationResponse(text=self.request.text, entities=entities)
        return response

    class Config:
        arbitrary_types_allowed = True
