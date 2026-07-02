import logging
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict

PII_ANNOTATION_LABELS = [
    "CARDINAL",
    "DATE",
    "EVENT",
    "FAC",
    "GPE",
    "LANGUAGE",
    "LAW",
    "LOC",
    "MONEY",
    "NORP",
    "ORDINAL",
    "ORG",
    "PERCENT",
    "PERSON",
    "PRODUCT",
    "QUANTITY",
    "TIME",
    "WORK_OF_ART",
]
MAXIMAL_STRING_SIZE = 1000000
DEFAULT_SPACY_MODEL = "en_core_web_lg"


class SpacyPIIAnnotator(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    nlp: Any
    model_name: str = DEFAULT_SPACY_MODEL

    @classmethod
    def create(cls, model_name: str = DEFAULT_SPACY_MODEL) -> "SpacyPIIAnnotator":
        try:
            import spacy
        except ImportError as exc:
            raise ImportError(
                "SpaCy engine requires the nlp extra. "
                "Install with: pip install datafog[nlp]"
            ) from exc

        try:
            nlp = spacy.load(model_name)
        except OSError as exc:
            raise ImportError(
                f"spaCy model {model_name!r} is not installed. "
                f"Download it explicitly with: datafog download-model {model_name} --engine spacy"
            ) from exc

        return cls(nlp=nlp, model_name=model_name)

    def annotate(self, text: str) -> Dict[str, List[str]]:
        try:
            if not text:
                return {label: [] for label in PII_ANNOTATION_LABELS}
            if len(text) > MAXIMAL_STRING_SIZE:
                text = text[:MAXIMAL_STRING_SIZE]
            doc = self.nlp(text)
            classified_entities: Dict[str, List[str]] = {
                label: [] for label in PII_ANNOTATION_LABELS
            }
            for ent in doc.ents:
                if ent.label_ in classified_entities:
                    classified_entities[ent.label_].append(ent.text)
            return classified_entities
        except Exception as e:
            logging.error(f"Error processing text for PII annotations: {str(e)}")
            return {
                label: [] for label in PII_ANNOTATION_LABELS
            }  # Return empty annotations in case of error
