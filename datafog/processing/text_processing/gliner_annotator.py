"""
GLiNER-based PII annotator for DataFog.

This module provides a GLiNER-based annotator for detecting PII entities in text.
GLiNER is a Generalist model for Named Entity Recognition that can identify any entity types.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from .regex_annotator.regex_annotator import AnnotationResult, Span

# Default entity types for PII detection using GLiNER
# These can be customized based on specific use cases
DEFAULT_PII_ENTITIES = [
    "person",
    "organization",
    "email",
    "phone number",
    "address",
    "credit card number",
    "social security number",
    "date of birth",
    "medical record number",
    "account number",
    "license number",
    "passport number",
    "ip address",
    "url",
    "location",
]

MAXIMAL_STRING_SIZE = 1000000


class GLiNERAnnotator(BaseModel):
    """
    GLiNER-based annotator for PII detection.

    Uses GLiNER models to detect various types of personally identifiable information
    in text. Supports custom entity types and provides flexible configuration.
    """

    model: Any
    entity_types: List[str]
    model_name: str

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    @classmethod
    def create(
        cls,
        model_name: str = "urchade/gliner_multi_pii-v1",
        entity_types: Optional[List[str]] = None,
    ) -> "GLiNERAnnotator":
        """
        Create a GLiNER annotator instance.

        Args:
            model_name: Name of the GLiNER model to use. Defaults to PII-specialized model.
            entity_types: List of entity types to detect. Defaults to common PII types.

        Returns:
            GLiNERAnnotator instance

        Raises:
            ImportError: If GLiNER dependencies are not installed
        """
        try:
            from gliner import GLiNER
        except ImportError:
            raise ImportError(
                "GLiNER dependencies not available. "
                "Install with: pip install datafog[nlp-advanced]"
            )

        if entity_types is None:
            entity_types = DEFAULT_PII_ENTITIES.copy()

        try:
            # Load the GLiNER model
            model = GLiNER.from_pretrained(model_name, local_files_only=True)
            logging.info(f"Successfully loaded GLiNER model: {model_name}")

            return cls(model=model, entity_types=entity_types, model_name=model_name)

        except Exception as e:
            logging.error(f"Failed to load GLiNER model {model_name}: {str(e)}")
            raise RuntimeError(
                f"GLiNER model {model_name!r} is not available locally. "
                "Download it explicitly with: "
                f"datafog download-model {model_name} --engine gliner"
            ) from e

    def annotate_with_spans(self, text: str):
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if len(text) > MAXIMAL_STRING_SIZE:
            raise ValueError(
                f"GLiNER input exceeds {MAXIMAL_STRING_SIZE} characters; split the document before scanning"
            )
        classified_entities = {
            label.upper().replace(" ", "_"): [] for label in self.entity_types
        }
        spans = []
        if text:
            try:
                entities = self.model.predict_entities(text, self.entity_types)
            except Exception as exc:
                raise RuntimeError("GLiNER annotation failed") from exc
            for entity in entities:
                label = entity["label"].upper().replace(" ", "_")
                classified_entities.setdefault(label, []).append(entity["text"])
                spans.append(
                    Span(
                        label=label,
                        start=entity["start"],
                        end=entity["end"],
                        text=entity["text"],
                    )
                )
        return classified_entities, AnnotationResult(text=text, spans=spans)

    def annotate(self, text: str) -> Dict[str, List[str]]:
        return self.annotate_with_spans(text)[0]

    def set_entity_types(self, entity_types: List[str]) -> None:
        """
        Update the entity types to detect.

        Args:
            entity_types: New list of entity types to detect
        """
        self.entity_types = entity_types
        logging.info(f"Updated entity types to: {entity_types}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "entity_types": self.entity_types,
            "max_text_size": MAXIMAL_STRING_SIZE,
        }

    @staticmethod
    def list_available_models() -> List[str]:
        """
        List popular GLiNER models available for download.

        Returns:
            List of model names
        """
        return [
            "urchade/gliner_base",
            "urchade/gliner_multi_pii-v1",
            "urchade/gliner_large-v2",
            "urchade/gliner_medium-v2.1",
            "knowledgator/gliner-bi-large-v1.0",
            "knowledgator/modern-gliner-bi-large-v1.0",
        ]

    @staticmethod
    def download_model(model_name: str) -> None:
        """
        Download and cache a GLiNER model.

        Args:
            model_name: Name of the model to download

        Raises:
            ImportError: If GLiNER dependencies are not installed
        """
        try:
            from gliner import GLiNER
        except ImportError:
            raise ImportError(
                "GLiNER dependencies not available. "
                "Install with: pip install datafog[nlp-advanced]"
            )

        try:
            # This will download and cache the model
            GLiNER.from_pretrained(model_name)
            logging.info(f"Successfully downloaded GLiNER model: {model_name}")
        except Exception as e:
            logging.error(f"Failed to download GLiNER model {model_name}: {str(e)}")
            raise
