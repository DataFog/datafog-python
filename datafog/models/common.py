"""
Common models for DataFog PII detection and annotation.

Defines entity types, patterns, and metadata structures used across the library.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class EntityTypes(str, Enum):
    """PII entity types recognized by DataFog."""

    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    EMAIL = "email address (containing @)"
    PHONE_NUMBER = (
        "phone number (containing numbers and possibly dashes or parentheses)"
    )
    DATE = "date (in any format)"
    NUMBER = "number (in any format)"
    CREDIT_CARD = "credit card number (in any format)"
    UNKNOWN = "UNKNOWN"


class Pattern(BaseModel):
    """Regex pattern for entity recognition."""

    name: str
    regex: str
    score: float


class PatternRecognizer(BaseModel):
    """Configuration for a pattern-based entity recognizer."""

    name: str
    supported_language: str
    patterns: List[Pattern]
    deny_list: Optional[List[str]] = None
    context: Optional[List[str]] = None
    supported_entity: str


class AnnotatorMetadata(BaseModel):
    """Metadata for annotation results."""

    recognizer_name: Optional[str] = None
