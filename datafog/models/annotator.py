"""
Defines data models for annotation requests and results.

Contains Pydantic models for structuring input, output, and explanations
in the annotation process. Ensures type safety and consistent data handling.
"""

from typing import List, Optional

from pydantic import BaseModel, field_validator

from .common import AnnotatorMetadata, EntityTypes, PatternRecognizer


class AnnotatorRequest(BaseModel):
    """
    Represents an annotation request.

    Contains text to annotate, language, and optional parameters
    to customize the annotation process.
    """

    text: str
    language: str
    correlation_id: Optional[str] = None
    score_threshold: Optional[float] = None
    entities: Optional[List[EntityTypes]] = None
    return_decision_process: Optional[bool] = None
    ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None
    context: Optional[List[str]] = None


class AnnotationResult(BaseModel):
    """
    Represents the result of an annotation.

    Includes position, score, entity type, and optional metadata.
    """

    start: int
    end: int
    score: Optional[float] = None
    entity_type: str
    recognition_metadata: Optional[AnnotatorMetadata] = None

    @field_validator("entity_type", mode="before")
    @classmethod
    def validate_entity_type(cls, v):
        from datafog.engine import ALL_ENTITY_TYPES, CANONICAL_TYPE_MAP

        if isinstance(v, EntityTypes):
            v = v.name
        v = CANONICAL_TYPE_MAP.get(v, v)
        return v if v in ALL_ENTITY_TYPES else "UNKNOWN"


class AnalysisExplanation(BaseModel):
    """
    Provides detailed explanation of an annotation analysis.

    Includes information about the recognizer, patterns, scores,
    and context improvements.
    """

    recognizer: str
    pattern_name: Optional[str] = None
    pattern: Optional[str] = None
    original_score: float
    score: float
    textual_explanation: Optional[str] = None
    score_context_improvement: float
    supportive_context_word: str
    validation_result: Optional[float] = None


class AnnotationResultWithAnaysisExplanation(AnnotationResult):
    """
    Extends AnnotationResult with detailed analysis explanation.
    """

    analysis_explanation: Optional[AnalysisExplanation] = None
