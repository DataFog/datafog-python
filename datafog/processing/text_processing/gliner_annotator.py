"""
GLiNER-based PII annotator for DataFog.

This module provides a GLiNER-based annotator for detecting PII entities in text.
GLiNER is a Generalist model for Named Entity Recognition that can identify any entity types.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

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
            model = GLiNER.from_pretrained(model_name)
            logging.info(f"Successfully loaded GLiNER model: {model_name}")

            return cls(model=model, entity_types=entity_types, model_name=model_name)

        except Exception as e:
            logging.error(f"Failed to load GLiNER model {model_name}: {str(e)}")
            raise

    def annotate(self, text: str) -> Dict[str, List[str]]:
        """
        Annotate text for PII entities using GLiNER.

        Args:
            text: Text to analyze for PII entities

        Returns:
            Dictionary mapping entity types to lists of detected entities
        """
        try:
            if not text:
                return {
                    entity_type.upper().replace(" ", "_"): []
                    for entity_type in self.entity_types
                }

            if len(text) > MAXIMAL_STRING_SIZE:
                text = text[:MAXIMAL_STRING_SIZE]
                logging.warning(f"Text truncated to {MAXIMAL_STRING_SIZE} characters")

            # Predict entities using GLiNER
            entities = self.model.predict_entities(text, self.entity_types)

            # Organize results by entity type
            classified_entities: Dict[str, List[str]] = {
                entity_type.upper().replace(" ", "_"): []
                for entity_type in self.entity_types
            }

            for entity in entities:
                entity_label = entity["label"].upper().replace(" ", "_")
                entity_text = entity["text"]

                if entity_label in classified_entities:
                    classified_entities[entity_label].append(entity_text)
                else:
                    # Handle cases where GLiNER returns entity types not in our list
                    classified_entities[entity_label] = [entity_text]

            return classified_entities

        except Exception as e:
            logging.error(f"Error processing text with GLiNER: {str(e)}")
            # Return empty annotations in case of error
            return {
                entity_type.upper().replace(" ", "_"): []
                for entity_type in self.entity_types
            }

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
