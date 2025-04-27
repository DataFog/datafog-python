"""
Provides spaCy-based NLP functionality for entity recognition and annotation.

This module implements a SpacyAnnotator class that uses spaCy models for
text annotation, entity recognition, and related NLP tasks.
"""

import logging
import threading
from typing import List, Optional
from uuid import uuid4

import spacy
from rich.progress import track
from spacy.language import Language  # For type hinting

from .annotator import AnnotationResult, AnnotatorRequest

# Set up logging
logger = logging.getLogger(__name__)

_SPACY_MODEL_CACHE = {}
_CACHE_LOCK = threading.Lock()


def _get_spacy_model(model_name: str) -> Language:
    """Loads a spaCy model, utilizing a cache to avoid redundant loads."""
    with _CACHE_LOCK:
        if model_name in _SPACY_MODEL_CACHE:
            logger.debug(f"Cache hit for model: {model_name!r}")
            return _SPACY_MODEL_CACHE[model_name]

        # Model not in cache, needs loading (lock ensures only one thread loads)
        logger.debug(f"Cache miss for model: {model_name!r}. Loading...")
        try:
            # Show progress for download
            if not spacy.util.is_package(model_name):
                logger.info(f"Model {model_name!r} not found. Downloading...")
                # Use rich.progress.track for visual feedback
                # This is a simplified representation; actual progress tracking might need
                # library integration or subprocess monitoring.
                # For now, just log the download attempt.
                spacy.cli.download(model_name)

            # Load the spaCy model after ensuring it's downloaded
            nlp = spacy.load(model_name)
            _SPACY_MODEL_CACHE[model_name] = nlp
            logger.debug(f"Model {model_name!r} loaded and cached.")
            return nlp
        except Exception as e:
            logger.error(f"Failed to load or download spaCy model {model_name}: {e}")
            raise


class SpacyAnnotator:
    """
    Handles text annotation using spaCy NLP models.

    Provides methods for loading models, annotating text, and managing spaCy resources.
    Supports various NLP tasks including entity recognition and model management.
    """

    def __init__(self, model_name: str = "en_core_web_lg"):
        self.model_name = model_name
        self.nlp = None  # Keep lazy loading

    def load_model(self):
        """Ensures the spaCy model is loaded, utilizing the cache."""
        if not self.nlp:
            # Use the cached loader function
            self.nlp = _get_spacy_model(self.model_name)

    def annotate_text(self, text: str, language: str = "en") -> List[AnnotationResult]:
        # This check now correctly uses the updated load_model -> _get_spacy_model
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
        # This check now correctly uses the updated load_model -> _get_spacy_model
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
        # Use the cached loader function for the default model
        nlp = _get_spacy_model("en_core_web_lg")
        return [ent for ent in nlp.pipe_labels["ner"]]
