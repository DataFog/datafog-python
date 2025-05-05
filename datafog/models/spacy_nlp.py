"""
Provides spaCy-based NLP functionality for entity recognition and annotation.

This module implements a SpacyAnnotator class that uses spaCy models for
text annotation, entity recognition, and related NLP tasks.
"""

from typing import List
from uuid import uuid4

import spacy
from rich.progress import track

from .annotator import AnnotationResult, AnnotatorRequest


class SpacyAnnotator:
    """
    Handles text annotation using spaCy NLP models.

    Provides methods for loading models, annotating text, and managing spaCy resources.
    Supports various NLP tasks including entity recognition and model management.
    """

    def __init__(self, model_name: str = "en_core_web_lg"):
        self.model_name = model_name
        self.nlp = None

    def load_model(self):
        if not spacy.util.is_package(self.model_name):
            spacy.cli.download(self.model_name)
        self.nlp = spacy.load(self.model_name)

    def annotate_text(self, text: str, language: str = "en") -> List[AnnotationResult]:
        if not self.nlp:
            self.load_model()

        annotator_request = AnnotatorRequest(
            text=text,
            language=language,
            correlation_id=str(uuid4()),
            score_threshold=0.5,
            entities=None,
            return_decision_process=False,
            ad_hoc_recognizers=None,
            context=None,
        )
        doc = self.nlp(annotator_request.text)
        results = []
        for ent in track(doc.ents, description="Processing entities"):
            result = AnnotationResult(
                start=ent.start_char,
                end=ent.end_char,
                score=0.8,  # Placeholder score
                entity_type=ent.label_,
                recognition_metadata=None,
            )
            results.append(result)
        return results

    def show_model_path(self) -> str:
        if not self.nlp:
            self.load_model()
        return str(self.nlp.path)

    @staticmethod
    def download_model(model_name: str):
        spacy.cli.download(model_name)

    @staticmethod
    def list_models() -> List[str]:
        return spacy.util.get_installed_models()

    @staticmethod
    def list_entities() -> List[str]:
        nlp = spacy.load("en_core_web_lg")
        return [ent for ent in nlp.pipe_labels["ner"]]
