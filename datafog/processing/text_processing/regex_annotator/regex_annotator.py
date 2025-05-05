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
            # Intentionally permissive to favor false positives over false negatives
            # Allows for multiple dots, special characters in local part, and subdomains
            # Note: This is broader than the spec to catch more potential emails
            "EMAIL": re.compile(
                r"""
                [\w!#$%&'*+\-/=?^_`{|}~.]+  # Local part with special chars allowed
                @                            # @ symbol
                [\w\-.]+                     # Domain name with possible dots
                \.[\w\-.]+                   # TLD with at least one dot
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Phone pattern - North American Numbering Plan (NANP) format
            # Accepts formats: 555-555-5555, (555) 555-5555, +1 555 555 5555, 1-555-555-5555
            # Note: Allows for various separators (dash, dot, space) and optional country code
            "PHONE": re.compile(
                r"""
                (?:(?:\+|)1[-\.\s]?)?      # Optional country code (+1 or 1)
                \(?\d{3}\)?                # Area code, optionally in parentheses
                [-\.\s]?                   # Optional separator after area code
                \d{3}                      # Exchange code
                [-\.\s]?                   # Optional separator after exchange code
                \d{4}                      # Subscriber number
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # SSN pattern - U.S. Social Security Number
            # Format: XXX-XX-XXXX where XXX != 000, 666
            # Note: Uses negative lookahead to reject invalid prefixes
            "SSN": re.compile(
                r"""
                \b                          # Word boundary
                (?!000|666)                # Reject 000 and 666 prefixes
                \d{3}                      # First 3 digits
                -                          # Hyphen separator
                \d{2}                      # Middle 2 digits
                -                          # Hyphen separator
                \d{4}                      # Last 4 digits
                \b                          # Word boundary
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Credit card pattern - Visa, Mastercard, and American Express
            # Visa: 16 digits, starts with 4
            # Mastercard: 16 digits, starts with 51-55
            # American Express: 15 digits, starts with 34 or 37 (EXACTLY 15 digits)
            # Note: Handles both continuous digit formats and formats with separators
            "CREDIT_CARD": re.compile(
                r"""
                \b
                (?:
                    4\d{12}(?:\d{3})?                      # Visa (16 digits, starts with 4)
                    |
                    5[1-5]\d{14}                           # Mastercard (16 digits, starts with 51-55)
                    |
                    3[47]\d{13}$                           # Amex (EXACTLY 15 digits, starts with 34 or 37)
                    |
                    (?:                                     # Formatted versions with separators
                        (?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})  # Card prefix
                        [-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}  # Rest of card with separators
                    )
                    |
                    (?:3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5})  # Amex with separators
                )
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # IP Address pattern - IPv4 and IPv6
            # IPv4: 4 octets of numbers 0-255 separated by dots
            # IPv6: 8 groups of 1-4 hex digits separated by colons, with possible compression
            # Note: Validates IPv4 octets to be in valid range (0-255)
            "IP_ADDRESS": re.compile(
                r"""
                (?:
                    # IPv4 address pattern
                    \b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b
                    |
                    # Simple IPv6 pattern that matches all valid formats including compressed ones
                    \b(?:[0-9a-f]{0,4}:){0,7}[0-9a-f]{0,4}\b
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Date of Birth pattern - supports MM/DD/YYYY, M/D/YYYY, MM-DD-YYYY, and YYYY-MM-DD formats
            # Note: Validates that month is 01-12 and day is 01-31
            "DOB": re.compile(
                r"""
                \b
                (?:
                    (?:0?[1-9]|1[0-2])                     # Month: 1-12
                    [/-]                                    # Separator (/ or -)
                    (?:0?[1-9]|[12][0-9]|3[01])            # Day: 1-31
                    [/-]                                    # Separator (/ or -)
                    (?:\d{2}|\d{4})                        # Year: 2 or 4 digits
                    |
                    (?:\d{4})                              # Year: 4 digits (ISO format)
                    -                                       # Separator (-)
                    (?:0?[1-9]|1[0-2])                     # Month: 1-12
                    -                                       # Separator (-)
                    (?:0?[1-9]|[12][0-9]|3[01])            # Day: 1-31
                )
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # ZIP code pattern - US ZIP / ZIP+4
            # Note: Supports both 5-digit ZIP and ZIP+4 format
            "ZIP": re.compile(
                r"""
                \b
                \d{5}                      # 5-digit ZIP code
                (?:-\d{4})?                # Optional +4 extension
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
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
        result: Dict[str, List[str]] = {label: [] for label in self.LABELS}

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
        spans_by_label: Dict[str, List[Span]] = {label: [] for label in self.LABELS}
        all_spans: List[Span] = []

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
                spans_by_label[label].append(span)
                all_spans.append(span)

        regex_result = {
            lbl: [s.text for s in spans_by_label[lbl]] for lbl in spans_by_label
        }

        return regex_result, AnnotationResult(text=text, spans=all_spans)
