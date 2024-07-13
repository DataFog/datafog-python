import logging
from typing import Any, Dict, List

from pydantic import BaseModel

PII_ANNOTATION_LABELS = ["DATE_TIME", "LOC", "NRP", "ORG", "PER"]
MAXIMAL_STRING_SIZE = 1000000


class SpacyPIIAnnotator(BaseModel):
    nlp: Any

    @classmethod
    def create(cls) -> "SpacyPIIAnnotator":
        try:
            # Try loading as a spaCy model first
            import spacy

            nlp = spacy.load("en_spacy_pii_fast")
        except OSError:
            # If that fails, try importing as a module
            try:
                import en_spacy_pii_fast

                nlp = en_spacy_pii_fast.load()
            except ImportError:
                raise ImportError(
                    "Failed to load en_spacy_pii_fast. Make sure it's installed correctly."
                )
        return cls(nlp=nlp)

    def annotate(self, text: str) -> Dict[str, List[str]]:
        try:
            if not text:
                return {label: [] for label in PII_ANNOTATION_LABELS}
            if len(text) > MAXIMAL_STRING_SIZE:
                text = text[:MAXIMAL_STRING_SIZE]
            doc = self.nlp(text)
            classified_entities = {label: [] for label in PII_ANNOTATION_LABELS}
            for ent in doc.ents:
                if ent.label_ in classified_entities:
                    classified_entities[ent.label_].append(ent.text)
            return classified_entities
        except Exception as e:
            logging.error(f"Error processing text for PII annotations: {str(e)}")
            return {
                label: [] for label in PII_ANNOTATION_LABELS
            }  # Return empty annotations in case of error

    class Config:
        arbitrary_types_allowed = True
