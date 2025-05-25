"""
Data models for anonymization requests and results.
"""

import hashlib
import secrets
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from .annotator import AnnotationResult
from .common import EntityTypes


class AnonymizerType(str, Enum):
    REDACT = "redact"
    REPLACE = "replace"
    HASH = "hash"


class HashType(str, Enum):
    MD5 = "md5"
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"


class AnonymizerRequest(BaseModel):
    text: str
    annotator_results: List[AnnotationResult]
    anonymizer_type: AnonymizerType
    entities: Optional[List[EntityTypes]] = None
    hash_type: Optional[HashType] = HashType.SHA256


class AnonymizationResult(BaseModel):
    anonymized_text: str
    anonymized_entities: List[dict] = Field(
        default_factory=list, alias="replaced_entities"
    )

    class Config:
        populate_by_name = True


class Anonymizer(BaseModel):
    anonymizer_type: AnonymizerType = AnonymizerType.REPLACE
    entities: Optional[List[EntityTypes]] = None
    hash_type: Optional[HashType] = HashType.SHA256

    def __init__(self, **data):
        super().__init__(**data)

    def anonymize(
        self, text: str, annotations: List[AnnotationResult]
    ) -> AnonymizationResult:
        """Anonymize PII in text based on the specified anonymizer type."""
        if self.anonymizer_type == AnonymizerType.REDACT:
            return self.redact_pii(text, annotations)
        elif self.anonymizer_type == AnonymizerType.REPLACE:
            return self.replace_pii(text, annotations)
        elif self.anonymizer_type == AnonymizerType.HASH:
            return self.hash_pii(text, annotations)
        else:
            raise ValueError(f"Unsupported anonymizer type: {self.anonymizer_type}")

    def replace_pii(
        self, text: str, annotations: List[AnnotationResult]
    ) -> AnonymizationResult:
        """Replace PII in text with anonymized values."""
        replacements = []
        for annotation in sorted(annotations, key=lambda x: x.start, reverse=True):
            if not self.entities or annotation.entity_type in self.entities:
                replacement = self._generate_replacement(
                    text[annotation.start : annotation.end], annotation.entity_type
                )
                replacements.append(
                    {
                        "original": text[annotation.start : annotation.end],
                        "replacement": replacement,
                        "entity_type": annotation.entity_type,
                    }
                )
                text = text[: annotation.start] + replacement + text[annotation.end :]

        return AnonymizationResult(
            anonymized_text=text, anonymized_entities=replacements
        )

    def _generate_replacement(self, original: str, entity_type: EntityTypes) -> str:
        """Generate a replacement for the given entity."""
        if entity_type == EntityTypes.PERSON:
            return f"[PERSON_{secrets.token_hex(4).upper()}]"
        elif entity_type == EntityTypes.ORGANIZATION:
            return f"[ORGANIZATION_{secrets.token_hex(4).upper()}]"
        elif entity_type == EntityTypes.LOCATION:
            return f"[LOCATION_{secrets.token_hex(4).upper()}]"
        elif entity_type == EntityTypes.DATE:
            return "[REDACTED_DATE]"
        else:
            return f"[{entity_type}_{secrets.token_hex(4).upper()}]"

    def hash_pii(
        self, text: str, annotations: List[AnnotationResult]
    ) -> AnonymizationResult:
        """Hash PII in text."""
        replacements = []
        for annotation in sorted(annotations, key=lambda x: x.start, reverse=True):
            if self.entities and annotation.entity_type not in self.entities:
                continue

            start, end = annotation.start, annotation.end
            original = text[start:end]
            replacement = self._hash_text(original)

            text = text[:start] + replacement + text[end:]
            replacements.append(
                {
                    "original": original,
                    "replacement": replacement,
                    "entity_type": annotation.entity_type,
                }
            )

        return AnonymizationResult(
            anonymized_text=text, anonymized_entities=replacements
        )

    def _hash_text(self, text: str) -> str:
        if self.hash_type == HashType.MD5:
            return hashlib.md5(text.encode()).hexdigest()
        elif self.hash_type == HashType.SHA256:
            return hashlib.sha256(text.encode()).hexdigest()
        elif self.hash_type == HashType.SHA3_256:
            return hashlib.sha3_256(text.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash type: {self.hash_type}")

    def redact_pii(
        self, text: str, annotations: List[AnnotationResult]
    ) -> AnonymizationResult:
        replacements = []
        for annotation in sorted(annotations, key=lambda x: x.start, reverse=True):
            if self.entities and annotation.entity_type not in self.entities:
                continue

            start, end = annotation.start, annotation.end
            original = text[start:end]
            replacement = "[REDACTED]"

            text = text[:start] + replacement + text[end:]
            replacements.append(
                {
                    "original": original,
                    "replacement": replacement,
                    "entity_type": annotation.entity_type,
                }
            )

        return AnonymizationResult(
            anonymized_text=text, anonymized_entities=replacements
        )
