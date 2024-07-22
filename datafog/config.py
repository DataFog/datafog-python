from enum import Enum


class OperationType(str, Enum):
    ANNOTATE_PII = "annotate_pii"
    EXTRACT_TEXT = "extract_text"
    REDACT_PII = "redact_pii"
    ANONYMIZE_PII = "anonymize_pii"
