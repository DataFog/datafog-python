"""Lean text processing service for PII annotation.

Provides synchronous and asynchronous methods for annotating text with personally
identifiable information (PII) using regex patterns. Supports chunking long texts
and batch processing. SpaCy integration available as optional extra.
"""

import asyncio
from typing import Dict, List, Union

from datafog.processing.text_processing.regex_annotator.regex_annotator import (
    RegexAnnotator,
    Span,
)


class TextService:
    """
    Lightweight service for annotating text with PII entities using regex patterns.

    This service provides methods to detect and annotate personally identifiable information (PII)
    in text using fast regex patterns. It supports chunking long texts for efficient processing
    and combining annotations from multiple chunks.

    For advanced NLP-based detection using spaCy, install the 'nlp' extra:
    pip install datafog[nlp]
    """

    def __init__(self, text_chunk_length: int = 1000, engine: str = "regex"):
        """
        Initialize the TextService with specified chunk length and annotation engine.

        Args:
            text_chunk_length: Maximum length of text chunks for processing. Default is 1000 characters.
            engine: The annotation engine to use. Options are:
                - "regex": (Default) Use RegexAnnotator for fast pattern-based entity detection
                - "spacy": Use SpacyPIIAnnotator for NLP-based entity detection (requires nlp extra)
                - "auto": Try RegexAnnotator first and fall back to SpacyPIIAnnotator if no entities found

        Raises:
            AssertionError: If an invalid engine type is provided
            ImportError: If spacy engine is requested but nlp extra is not installed
        """
        assert engine in {"regex", "spacy", "auto"}, "Invalid engine"
        self.engine = engine
        self.regex_annotator = RegexAnnotator()
        self.text_chunk_length = text_chunk_length

        # Only initialize spacy if needed and available
        self.spacy_annotator = None
        if engine in {"spacy", "auto"}:
            try:
                from datafog.processing.text_processing.spacy_pii_annotator import (
                    SpacyPIIAnnotator,
                )

                self.spacy_annotator = SpacyPIIAnnotator.create()
            except ImportError:
                if engine == "spacy":
                    raise ImportError(
                        "SpaCy engine requires additional dependencies. "
                        "Install with: pip install datafog[nlp]"
                    )
                # For auto mode, just continue with regex only
                self.spacy_annotator = None

    def _chunk_text(self, text: str) -> List[str]:
        """Split the text into chunks of specified length."""
        return [
            text[i : i + self.text_chunk_length]
            for i in range(0, len(text), self.text_chunk_length)
        ]

    def _combine_annotations(
        self, chunk_annotations: List[Dict[str, List[str]]]
    ) -> Dict[str, List[str]]:
        """Combine annotations from multiple chunks."""
        combined = {}
        for annotations in chunk_annotations:
            for entity_type, entities in annotations.items():
                if entity_type not in combined:
                    combined[entity_type] = []
                combined[entity_type].extend(entities)
        return combined

    def annotate_text_sync(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List[Span]]:
        """
        Annotate text synchronously for PII entities.

        Args:
            text: The text to annotate
            structured: If True, return structured Span objects. If False, return dict format.

        Returns:
            Dictionary mapping entity types to lists of entities, or list of Span objects
        """
        if len(text) <= self.text_chunk_length:
            # Single chunk processing
            if self.engine == "regex":
                if structured:
                    _, result = self.regex_annotator.annotate_with_spans(text)
                    return result.spans
                return self.regex_annotator.annotate(text)
            elif self.engine == "spacy":
                if self.spacy_annotator is None:
                    raise ImportError(
                        "SpaCy engine not available. Install with: pip install datafog[nlp]"
                    )
                return self.spacy_annotator.annotate(text)
            elif self.engine == "auto":
                # Try regex first
                regex_result = self.regex_annotator.annotate(text)

                # Check if regex found any entities
                if any(entities for entities in regex_result.values()):
                    if structured:
                        _, result = self.regex_annotator.annotate_with_spans(text)
                        return result.spans
                    return regex_result

                # Fall back to spacy if available
                if self.spacy_annotator is not None:
                    return self.spacy_annotator.annotate(text)

                # Return regex result even if empty
                if structured:
                    _, result = self.regex_annotator.annotate_with_spans(text)
                    return result.spans
                return regex_result
        else:
            # Multi-chunk processing
            chunks = self._chunk_text(text)
            chunk_annotations = []

            for chunk in chunks:
                chunk_result = self.annotate_text_sync(chunk, structured=False)
                chunk_annotations.append(chunk_result)

            if structured:
                # For structured output with chunking, we need to recalculate positions
                # This is more complex, so for now return dict format
                return self._combine_annotations(chunk_annotations)

            return self._combine_annotations(chunk_annotations)

    async def annotate_text_async(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List[Span]]:
        """
        Annotate text asynchronously for PII entities.

        Args:
            text: The text to annotate
            structured: If True, return structured Span objects. If False, return dict format.

        Returns:
            Dictionary mapping entity types to lists of entities, or list of Span objects
        """
        # For regex processing, we can just run synchronously since it's fast
        return self.annotate_text_sync(text, structured)

    def batch_annotate_text_sync(self, texts: List[str]) -> List[Dict[str, List[str]]]:
        """
        Annotate multiple texts synchronously.

        Args:
            texts: List of texts to annotate

        Returns:
            List of annotation dictionaries, one per input text
        """
        return [self.annotate_text_sync(text) for text in texts]

    async def batch_annotate_text_async(
        self, texts: List[str]
    ) -> List[Dict[str, List[str]]]:
        """
        Annotate multiple texts asynchronously.

        Args:
            texts: List of texts to annotate

        Returns:
            List of annotation dictionaries, one per input text
        """
        # For better performance with many texts, we can process them concurrently
        tasks = [self.annotate_text_async(text) for text in texts]
        return await asyncio.gather(*tasks)
