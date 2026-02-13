"""Lean text processing service for PII annotation.

Provides synchronous and asynchronous methods for annotating text with personally
identifiable information (PII) using regex patterns. Supports chunking long texts
and batch processing. SpaCy integration available as optional extra.
"""

import asyncio
import warnings
from typing import TYPE_CHECKING, Dict, List, Union

if TYPE_CHECKING:
    from datafog.processing.text_processing.regex_annotator.regex_annotator import Span
else:
    # Runtime import for Span when needed
    Span = None


def _get_span_class():
    """Lazily import Span class when needed."""
    global Span
    if Span is None:
        from datafog.processing.text_processing.regex_annotator.regex_annotator import (
            Span,
        )
    return Span


class TextService:
    """
    Lightweight service for annotating text with PII entities using regex patterns.

    This service provides methods to detect and annotate personally identifiable information (PII)
    in text using fast regex patterns. It supports chunking long texts for efficient processing
    and combining annotations from multiple chunks.

    For advanced NLP-based detection using spaCy, install the 'nlp' extra:
    pip install datafog[nlp]
    """

    def __init__(
        self,
        text_chunk_length: int = 1000,
        engine: str = "regex",
        gliner_model: str = "urchade/gliner_multi_pii-v1",
    ):
        """
        Initialize the TextService with specified chunk length and annotation engine.

        Args:
            text_chunk_length: Maximum length of text chunks for processing. Default is 1000 characters.
            engine: The annotation engine to use. Options are:
                - "regex": (Default) Use RegexAnnotator for fast pattern-based entity detection
                - "spacy": Use SpacyPIIAnnotator for NLP-based entity detection (requires nlp extra)
                - "gliner": Use GLiNERAnnotator for ML-based entity detection (requires nlp-advanced extra)
                - "auto": Try RegexAnnotator first and fall back to SpacyPIIAnnotator if no entities found
                - "smart": Try RegexAnnotator → GLiNER → SpaCy cascade (requires nlp-advanced extra)
            gliner_model: GLiNER model name to use when engine is "gliner" or "smart"

        Raises:
            AssertionError: If an invalid engine type is provided
            ImportError: If spacy/gliner engine is requested but corresponding extra is not installed
        """
        assert engine in {"regex", "spacy", "gliner", "auto", "smart"}, "Invalid engine"
        self.engine = engine
        self.text_chunk_length = text_chunk_length
        self.gliner_model = gliner_model

        # Lazy initialization - annotators created only when needed
        self._regex_annotator = None
        self._spacy_annotator = None
        self._gliner_annotator = None
        self._spacy_import_attempted = False
        self._gliner_import_attempted = False
        self._warned_missing_spacy = False
        self._warned_missing_gliner = False

        # For engine-specific modes, validate dependencies at init time
        if engine == "spacy":
            self._ensure_spacy_available()
        elif engine == "gliner":
            self._ensure_gliner_available()

        try:
            from datafog.telemetry import track_function_call

            track_function_call(
                function_name="TextService.__init__",
                module="datafog.services.text_service",
                engine=engine,
                text_chunk_length=text_chunk_length,
                gliner_model=gliner_model if engine in ("gliner", "smart") else None,
            )
        except Exception:
            pass

    @property
    def regex_annotator(self):
        """Lazy-loaded regex annotator."""
        if self._regex_annotator is None:
            from datafog.processing.text_processing.regex_annotator.regex_annotator import (
                RegexAnnotator,
            )

            self._regex_annotator = RegexAnnotator()
        return self._regex_annotator

    @property
    def spacy_annotator(self):
        """Lazy-loaded spaCy annotator."""
        if self._spacy_annotator is None and not self._spacy_import_attempted:
            self._spacy_annotator = self._create_spacy_annotator()
            self._spacy_import_attempted = True
        return self._spacy_annotator

    @property
    def gliner_annotator(self):
        """Lazy-loaded GLiNER annotator."""
        if self._gliner_annotator is None and not self._gliner_import_attempted:
            self._gliner_annotator = self._create_gliner_annotator()
            self._gliner_import_attempted = True
        return self._gliner_annotator

    def _ensure_spacy_available(self):
        """Ensure spaCy dependencies are available, raise ImportError if not."""
        try:
            import spacy  # noqa: F401
        except ImportError:
            raise ImportError(
                "SpaCy engine requires additional dependencies. "
                "Install with: pip install datafog[nlp]"
            )

    def _ensure_gliner_available(self):
        """Ensure GLiNER dependencies are available, raise ImportError if not."""
        try:
            from gliner import GLiNER  # noqa: F401
        except ImportError:
            raise ImportError(
                "GLiNER engine requires additional dependencies. "
                "Install with: pip install datafog[nlp-advanced]"
            )

    def _create_spacy_annotator(self):
        """Create spaCy annotator if dependencies are available."""
        try:
            from datafog.processing.text_processing.spacy_pii_annotator import (
                SpacyPIIAnnotator,
            )

            return SpacyPIIAnnotator.create()
        except ImportError:
            return None

    def _create_gliner_annotator(self):
        """Create GLiNER annotator if dependencies are available."""
        try:
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            return GLiNERAnnotator.create(model_name=self.gliner_model)
        except ImportError:
            return None

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

    def _cascade_should_stop(self, engine: str, result: Dict[str, List[str]]) -> bool:
        """
        Determine if the cascade should stop based on the engine results.

        Simple MVP logic: stop if we found any entities for regex,
        or 2+ entities for GLiNER.
        """
        total_entities = sum(len(entities) for entities in result.values())

        if engine == "regex":
            # Stop if we found any structured PII (high confidence)
            return total_entities >= 1
        elif engine == "gliner":
            # Stop if we found multiple entities (reasonable coverage)
            return total_entities >= 2

        return False  # Always run spaCy as final step

    def _annotate_with_smart_cascade(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List["Span"]]:
        """
        Annotate text using smart cascading: regex → GLiNER → spaCy.

        Args:
            text: Text to annotate
            structured: Whether to return structured spans

        Returns:
            Annotations from the first engine that finds sufficient entities
        """
        # Stage 1: Try regex first (fastest)
        if structured:
            # For structured output, use annotate_with_spans directly to avoid double processing
            _, result = self.regex_annotator.annotate_with_spans(text)
            regex_result = {}
            for span in result.spans:
                if span.label not in regex_result:
                    regex_result[span.label] = []
                regex_result[span.label].append(span.text)

            if self._cascade_should_stop("regex", regex_result):
                return result.spans
        else:
            regex_result = self.regex_annotator.annotate(text)
            if self._cascade_should_stop("regex", regex_result):
                return regex_result

        # Stage 2: Try GLiNER (balanced speed/accuracy)
        if self.gliner_annotator is not None:
            gliner_result = self.gliner_annotator.annotate(text)
            if self._cascade_should_stop("gliner", gliner_result):
                # Note: GLiNER doesn't support structured output yet, return dict
                return gliner_result
        elif not self._warned_missing_gliner:
            warnings.warn(
                "GLiNER not available, smart cascade will run without GLiNER. "
                "Install with: pip install datafog[nlp-advanced]",
                UserWarning,
                stacklevel=2,
            )
            self._warned_missing_gliner = True

        # Stage 3: Fall back to spaCy (most comprehensive)
        if self.spacy_annotator is not None:
            return self.spacy_annotator.annotate(text)
        if not self._warned_missing_spacy:
            warnings.warn(
                "SpaCy not available, smart cascade will run without spaCy. "
                "Install with: pip install datafog[nlp]",
                UserWarning,
                stacklevel=2,
            )
            self._warned_missing_spacy = True

        # Return best available result
        if self.gliner_annotator is not None:
            return self.gliner_annotator.annotate(text)

        # Final fallback to regex
        if structured:
            _, result = self.regex_annotator.annotate_with_spans(text)
            return result.spans
        return regex_result

    def _annotate_single_chunk(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List["Span"]]:
        """Annotate a single chunk of text based on the engine type."""
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
        elif self.engine == "gliner":
            if self.gliner_annotator is None:
                raise ImportError(
                    "GLiNER engine not available. Install with: pip install datafog[nlp-advanced]"
                )
            return self.gliner_annotator.annotate(text)
        elif self.engine == "smart":
            return self._annotate_with_smart_cascade(text, structured)
        elif self.engine == "auto":
            return self._annotate_with_auto_engine(text, structured)

    def _annotate_with_auto_engine(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List["Span"]]:
        """Handle auto engine annotation with regex fallback to spacy."""
        # Try regex first
        if structured:
            # For structured output, use annotate_with_spans directly to avoid double processing
            _, result = self.regex_annotator.annotate_with_spans(text)
            regex_result = {}
            for span in result.spans:
                if span.label not in regex_result:
                    regex_result[span.label] = []
                regex_result[span.label].append(span.text)

            # Check if regex found any entities
            if any(entities for entities in regex_result.values()):
                return result.spans
        else:
            regex_result = self.regex_annotator.annotate(text)

            # Check if regex found any entities
            if any(entities for entities in regex_result.values()):
                return regex_result

        # Fall back to spacy if available
        if self.spacy_annotator is not None:
            return self.spacy_annotator.annotate(text)

        # Return regex result even if empty
        if structured:
            # We already have the result from above in structured mode
            return result.spans
        return regex_result

    def _annotate_multiple_chunks_structured(self, chunks: List[str]) -> List["Span"]:
        """Handle structured annotation across multiple chunks."""
        all_spans = []
        current_offset = 0

        # Get Span class once outside the loop for efficiency
        SpanClass = _get_span_class()

        for chunk in chunks:
            chunk_spans = self._annotate_single_chunk(chunk, structured=True)
            # Adjust span positions to account for chunk offset
            for span in chunk_spans:
                adjusted_span = SpanClass(
                    start=span.start + current_offset,
                    end=span.end + current_offset,
                    text=span.text,
                    label=span.label,
                )
                all_spans.append(adjusted_span)
            current_offset += len(chunk)

        return all_spans

    def _annotate_multiple_chunks_dict(self, chunks: List[str]) -> Dict[str, List[str]]:
        """Handle dictionary annotation across multiple chunks."""
        chunk_annotations = []
        for chunk in chunks:
            chunk_result = self._annotate_single_chunk(chunk, structured=False)
            chunk_annotations.append(chunk_result)
        return self._combine_annotations(chunk_annotations)

    def annotate_text_sync(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List["Span"]]:
        """
        Annotate text synchronously for PII entities.

        Args:
            text: The text to annotate
            structured: If True, return structured Span objects. If False, return dict format.

        Returns:
            Dictionary mapping entity types to lists of entities, or list of Span objects
        """
        import time as _time

        _start = _time.monotonic()

        if len(text) <= self.text_chunk_length:
            # Single chunk processing
            result = self._annotate_single_chunk(text, structured)
        else:
            # Multi-chunk processing
            chunks = self._chunk_text(text)

            if structured:
                result = self._annotate_multiple_chunks_structured(chunks)
            else:
                result = self._annotate_multiple_chunks_dict(chunks)

        try:
            from datafog.telemetry import (
                _get_duration_bucket,
                _get_text_length_bucket,
                track_function_call,
            )

            _duration = (_time.monotonic() - _start) * 1000
            track_function_call(
                function_name="TextService.annotate_text_sync",
                module="datafog.services.text_service",
                engine=self.engine,
                text_length_bucket=_get_text_length_bucket(len(text)),
                structured=structured,
                duration_ms_bucket=_get_duration_bucket(_duration),
            )
        except Exception:
            pass

        return result

    async def annotate_text_async(
        self, text: str, structured: bool = False
    ) -> Union[Dict[str, List[str]], List["Span"]]:
        """
        Annotate text asynchronously for PII entities.

        Args:
            text: The text to annotate
            structured: If True, return structured Span objects. If False, return dict format.

        Returns:
            Dictionary mapping entity types to lists of entities, or list of Span objects
        """
        # Run sync processing on a worker thread so async callers avoid event-loop blocking.
        return await asyncio.to_thread(self.annotate_text_sync, text, structured)

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
