import re
from typing import Dict, List, Pattern, Tuple

from pydantic import BaseModel


class Span(BaseModel):
    """Represents a span of text with a label and character offsets."""

    label: str  # "EMAIL"
    start: int  # char offset
    end: int  # char offset
    text: str  # The actual text content


class AnnotationResult(BaseModel):
    """Structured model for annotation results."""

    text: str  # The input text
    spans: List[Span]  # List of spans found in the text


class RegexAnnotator:
    """Annotator that uses regular expressions to identify PII entities in text.

    This annotator serves as a fallback to the SpaCy annotator and is optimized for
    performance, targeting ≤ 20 µs / kB on a MacBook M-series.
    """

    # Labels for PII entities
    LABELS = ["EMAIL", "PHONE", "SSN", "CREDIT_CARD", "IP_ADDRESS", "DOB", "ZIP"]

    def __init__(self):
        # Compile all patterns once at initialization
        self.patterns: Dict[str, Pattern] = {
            # Email pattern - RFC 5322 subset
            # Allows for multiple dots, special characters in local part, and subdomains
            # The pattern is intentionally permissive to favor false positives over false negatives
            "EMAIL": re.compile(
                r"[\w!#$%&\'*+\-/=?^_`{|}~.]+@[\w\-.]+\.[\w\-.]+",
                re.IGNORECASE | re.MULTILINE,
            ),
            # Phone pattern - NANP (North American Numbering Plan) format
            # Accepts formats like: 555-555-5555, (555) 555-5555, +1 555 555 5555, 1-555-555-5555
            "PHONE": re.compile(
                r"(?:(?:\+|)1[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
                re.IGNORECASE | re.MULTILINE,
            ),
            # SSN pattern - U.S. Social Security Number
            # Format: XXX-XX-XXXX where XXX != 000, 666
            "SSN": re.compile(
                r"\b(?!000|666)\d{3}-\d{2}-\d{4}\b", re.IGNORECASE | re.MULTILINE
            ),
            # Credit card pattern - Visa, Mastercard, and American Express
            # Visa: 16 digits, starts with 4
            # Mastercard: 16 digits, starts with 51-55
            # American Express: 15 digits, starts with 34 or 37
            "CREDIT_CARD": re.compile(
                r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|(?:(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})|(?:3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}))\b",
                re.IGNORECASE | re.MULTILINE,
            ),
            # IP Address pattern - IPv4 and IPv6
            # IPv4: 4 octets of numbers 0-255 separated by dots
            # IPv6: 8 groups of 1-4 hex digits separated by colons, with possible compression
            "IP_ADDRESS": re.compile(
                r"(?:\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b|\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b|\b(?:[A-Fa-f0-9]{1,4}:){0,6}(?::[A-Fa-f0-9]{1,4}){1,6}\b|\b(?:[A-Fa-f0-9]{1,4}:){1,7}:\b)",
                re.IGNORECASE | re.MULTILINE,
            ),
            # Date of Birth pattern - supports MM/DD/YYYY, M/D/YYYY, MM-DD-YYYY, and YYYY-MM-DD formats
            # Validates that month is 01-12 and day is 01-31 for MM/DD/YYYY format
            "DOB": re.compile(
                r"\b(?:(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:\d{2}|\d{4})|(?:\d{4})-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12][0-9]|3[01]))\b",
                re.IGNORECASE | re.MULTILINE,
            ),
            "ZIP": re.compile(r"\b\d{5}(?:-\d{4})?\b", re.IGNORECASE | re.MULTILINE),
        }

    @classmethod
    def create(cls) -> "RegexAnnotator":
        """Factory method to create a new RegexAnnotator instance."""
        return cls()

    def annotate(self, text: str) -> Dict[str, List[str]]:
        """Annotate text with PII entities using regex patterns.

        Args:
            text: The input text to annotate

        Returns:
            A dictionary mapping entity labels to lists of matched strings
        """
        result = {label: [] for label in self.LABELS}

        # Return empty result for empty text
        if not text:
            return result

        # Process with each pattern
        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                result[label].append(match.group())

        return result

    def annotate_with_spans(
        self, text: str
    ) -> Tuple[Dict[str, List[str]], AnnotationResult]:
        """Annotate text and return both dict format and structured format.

        Args:
            text: The input text to annotate

        Returns:
            A tuple containing:
            - A dictionary mapping entity labels to lists of matched strings
            - An AnnotationResult object with structured span information
        """
        spans_by_label = {label: [] for label in self.LABELS}
        all_spans = []

        if not text:
            return spans_by_label, AnnotationResult(text=text, spans=all_spans)

        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                span = Span(
                    label=label,
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                )
                spans_by_label.setdefault(label, []).append(span)
                all_spans.append(span)

        regex_result = {
            lbl: [s.text for s in spans_by_label[lbl]] for lbl in spans_by_label
        }

        return regex_result, AnnotationResult(text=text, spans=all_spans)
