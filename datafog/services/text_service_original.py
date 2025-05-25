"""Text processing service for PII annotation.

Provides synchronous and asynchronous methods for annotating text with personally identifiable information (PII) using SpaCy or regex patterns. Supports chunking long texts and batch processing.
"""

import asyncio
from typing import Dict, List, Union

from datafog.processing.text_processing.regex_annotator.regex_annotator import (
    RegexAnnotator,
    Span,
)
from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator


class TextService:
    """
    Service for annotating text with PII entities.

    This service provides methods to detect and annotate personally identifiable information (PII)
    in text using different annotation engines. It supports chunking long texts for efficient processing
    and combining annotations from multiple chunks.
    """

    def __init__(self, text_chunk_length: int = 1000, engine: str = "auto"):
        """
        Initialize the TextService with specified chunk length and annotation engine.

        Args:
            text_chunk_length: Maximum length of text chunks for processing. Default is 1000 characters.
            engine: The annotation engine to use. Options are:
                - "regex": Use only the RegexAnnotator for pattern-based entity detection
                - "spacy": Use only the SpacyPIIAnnotator for NLP-based entity detection
                - "auto": (Default) Try RegexAnnotator first and fall back to SpacyPIIAnnotator if no entities are found

        Raises:
            AssertionError: If an invalid engine type is provided
        """
        assert engine in {"regex", "spacy", "auto"}, "Invalid engine"
        self.engine = engine
        self.spacy_annotator = SpacyPIIAnnotator.create()
        self.regex_annotator = RegexAnnotator()
        self.text_chunk_length = text_chunk_length

    def _chunk_text(self, text: str) -> List[str]:
        """Split the text into chunks of specified length."""
        return [
            text[i : i + self.text_chunk_length]
            for i in range(0, len(text), self.text_chunk_length)
        ]

    def _combine_annotations(
        self, annotations: List[Dict[str, List[str]]]
    ) -> Dict[str, List[str]]:
        """Combine annotations from multiple chunks."""
        combined: Dict[str, List[str]] = {}
        for annotation in annotations:
            for key, value in annotation.items():
                if key not in combined:
                    combined[key] = []
                combined[key].extend(value)
        return combined

    def _annotate_with_engine(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List[Span]]:
        """
        Annotate text using the selected engine based on the engine parameter.

        This method implements the engine selection logic:
        - For "regex" mode: Uses only the RegexAnnotator
        - For "spacy" mode: Uses only the SpacyPIIAnnotator
        - For "auto" mode: Tries RegexAnnotator first and falls back to SpacyPIIAnnotator if no entities are found

        Args:
            text: The text to annotate
            structured: If True, return structured output (list of Span objects)

        Returns:
            If structured=False: Dictionary of annotations by entity type where keys are entity types (e.g., "EMAIL", "PERSON", "ORG")
                and values are lists of detected entities of that type
            If structured=True: List of Span objects with entity information
        """
        if structured:
            # Handle structured output mode
            if self.engine == "regex":
                _, annotation_result = self.regex_annotator.annotate_with_spans(text)
                return annotation_result.spans
            elif self.engine == "spacy":
                # For spaCy, we need to convert the dictionary format to spans
                spacy_dict = self.spacy_annotator.annotate(text)
                spacy_spans: List[Span] = []
                for label, entities in spacy_dict.items():
                    for entity in entities:
                        # Find the start and end positions of the entity in the text
                        start = text.find(entity)
                        if start >= 0:
                            end = start + len(entity)
                            span = Span(start=start, end=end, label=label, text=entity)
                            spacy_spans.append(span)
                return spacy_spans
            else:  # "auto" mode
                # Try regex first
                _, annotation_result = self.regex_annotator.annotate_with_spans(text)
                if annotation_result.spans:
                    return annotation_result.spans

                # If regex found nothing, fall back to spaCy
                spacy_dict = self.spacy_annotator.annotate(text)
                auto_spans: List[Span] = []
                for label, entities in spacy_dict.items():
                    for entity in entities:
                        # Find the start and end positions of the entity in the text
                        start = text.find(entity)
                        if start >= 0:
                            end = start + len(entity)
                            span = Span(start=start, end=end, label=label, text=entity)
                            auto_spans.append(span)
                return auto_spans
        else:
            # Handle legacy dictionary output mode
            if self.engine == "regex":
                return self.regex_annotator.annotate(text)
            elif self.engine == "spacy":
                return self.spacy_annotator.annotate(text)
            else:  # auto mode
                # Try regex first
                regex_dict = self.regex_annotator.annotate(text)

                # Check if any VALID entities were found (ignore empty strings)
                has_entities = any(
                    any(entity.strip() for entity in entities)
                    for entities in regex_dict.values()
                )

                # If regex found entities, return those results
                if has_entities:
                    return regex_dict

                # Otherwise, fall back to spaCy
                return self.spacy_annotator.annotate(text)

    def annotate_text_sync(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List[Span]]:
        """
        Synchronously annotate a text string.

        Args:
            text: The text to annotate
            structured: If True, return structured output (list of Span objects)

        Returns:
            If structured=False: Dictionary mapping entity types to lists of strings
            If structured=True: List of Span objects with entity information
        """
        if not text:
            return [] if structured else {}

        chunks = self._chunk_text(text)

        if structured:
            # Handle structured output mode
            all_spans: List[Span] = []
            chunk_offset = 0  # Track the offset for each chunk in the original text

            for chunk in chunks:
                # Process each chunk and get spans
                chunk_spans = self._annotate_with_engine(chunk, structured=True)
                if not isinstance(chunk_spans, list):
                    continue  # Skip if not a list of spans

                # Adjust span positions based on chunk offset in the original text
                for span in chunk_spans:
                    if not isinstance(span, Span):
                        continue  # Skip if not a Span object
                    span.start += chunk_offset
                    span.end += chunk_offset
                    # Verify the span text matches the text at the adjusted position
                    if span.start < len(text) and span.end <= len(text):
                        span.text = text[span.start : span.end]
                        all_spans.append(span)

                # Update offset for the next chunk
                chunk_offset += len(chunk)

            print(f"Done processing {text.split()[0]}")
            return all_spans
        else:
            # Handle legacy dictionary output mode
            annotations: List[Dict[str, List[str]]] = []
            for chunk in chunks:
                res = self._annotate_with_engine(chunk)
                if isinstance(res, dict):
                    annotations.append(res)
            combined = self._combine_annotations(annotations)
            print(f"Done processing {text.split()[0]}")
            return combined

    def batch_annotate_text_sync(
        self, texts: List[str], structured: bool = False
    ) -> Dict[str, Union[Dict[str, List[str]], List[Span]]]:
        """
        Synchronously annotate a list of text input.

        Args:
            texts: List of text strings to annotate
            structured: If True, return structured output (list of Span objects) for each text

        Returns:
            Dictionary mapping each input text to its annotation result
        """
        results = [
            self.annotate_text_sync(text, structured=structured) for text in texts
        ]
        return dict(zip(texts, results, strict=True))

    async def annotate_text_async(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List[Span]]:
        """
        Asynchronously annotate a text string.

        Args:
            text: The text to annotate
            structured: If True, return structured output (list of Span objects)

        Returns:
            If structured=False: Dictionary mapping entity types to lists of strings
            If structured=True: List of Span objects with entity information
        """
        if not text:
            return [] if structured else {}

        chunks = self._chunk_text(text)

        if structured:
            # Handle structured output mode asynchronously
            all_spans: List[Span] = []
            chunk_offset = 0  # Track the offset for each chunk in the original text

            for chunk in chunks:
                # We can't easily parallelize this due to the need to track offsets sequentially
                # In a production environment, you might want a more sophisticated approach
                chunk_spans = self._annotate_with_engine(chunk, structured=True)
                if not isinstance(chunk_spans, list):
                    continue  # Skip if not a list of spans

                # Adjust span positions based on chunk offset in the original text
                for span in chunk_spans:
                    if not isinstance(span, Span):
                        continue  # Skip if not a Span object
                    span.start += chunk_offset
                    span.end += chunk_offset
                    # Verify the span text matches the text at the adjusted position
                    if span.start < len(text) and span.end <= len(text):
                        span.text = text[span.start : span.end]
                        all_spans.append(span)

                # Update offset for the next chunk
                chunk_offset += len(chunk)

            return all_spans
        else:
            # Handle legacy dictionary output mode asynchronously
            tasks = [
                asyncio.to_thread(self._annotate_with_engine, chunk) for chunk in chunks
            ]
            results = await asyncio.gather(*tasks)
            annotations: List[Dict[str, List[str]]] = [
                r for r in results if isinstance(r, dict)
            ]
            return self._combine_annotations(annotations)

    async def batch_annotate_text_async(
        self, texts: List[str], structured: bool = False
    ) -> Dict[str, Union[Dict[str, List[str]], List[Span]]]:
        """
        Asynchronously annotate a list of text input.

        Args:
            texts: List of text strings to annotate
            structured: If True, return structured output (list of Span objects) for each text

        Returns:
            Dictionary mapping each input text to its annotation result
        """
        tasks = [
            self.annotate_text_async(text, structured=structured) for text in texts
        ]
        results = await asyncio.gather(*tasks)
        return dict(zip(texts, results, strict=True))
