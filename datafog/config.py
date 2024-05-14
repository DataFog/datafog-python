from enum import Enum

from pydantic import BaseModel


class OperationType(str, Enum):
    ANNOTATE_PII = "annotate_pii"
    EXTRACT_TEXT = "extract_text"
    REDACT_PII = "redact_pii"
    ANONYMIZE_PII = "anonymize_pii"
