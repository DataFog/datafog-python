import re
from typing import Callable, Dict, Iterable, List, Optional, Pattern, Set, Tuple

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

    Locale notes:
        German-specific entity types (DE_*) are disabled by default. Enable them by
        passing locales=["de"]. This avoids false positives on non-German text.
    """

    # Labels for PII entities
    BASE_LABELS = [
        "EMAIL",
        "PHONE",
        "SSN",
        "CREDIT_CARD",
        "IP_ADDRESS",
        "DOB",
        "ZIP",
    ]

    LOCALE_LABELS = {
        "de": [
            "DE_VAT_ID",
            "DE_IBAN",
            "DE_TAX_ID",
            "DE_SOCIAL_SECURITY_NUMBER",
            "DE_POSTAL_CODE",
            "DE_PASSPORT_NUMBER",
            "DE_RESIDENCE_PERMIT_NUMBER",
        ],
    }

    LABELS = BASE_LABELS + LOCALE_LABELS["de"]

    _DE_PASSPORT_PREFIXES = "CFGHJKLMNPRTVWXYZ"
    _DE_RESIDENCE_CONTEXT_RE = re.compile(
        r"\b(aufenthaltstitel|aufenthaltserlaubnis|aufenthaltskarte|residence permit|residence card)\b",
        re.IGNORECASE,
    )

    def __init__(self, locales: Optional[Iterable[str]] = None):
        self.locales = self._normalize_locales(locales)
        self.active_labels = self._labels_for_locales(self.locales)

        # Compile all patterns once at initialization
        self.patterns = self._compile_patterns()
        self.validators = self._build_validators()

    @staticmethod
    def _normalize_locales(locales: Optional[Iterable[str]]) -> Set[str]:
        if locales is None:
            return set()
        if isinstance(locales, str):
            values = [locales]
        else:
            values = list(locales)
        normalized = {
            value.strip().lower()
            for value in values
            if isinstance(value, str) and value.strip()
        }
        return normalized

    @classmethod
    def labels_for_locales(cls, locales: Optional[Iterable[str]] = None) -> List[str]:
        normalized = cls._normalize_locales(locales)
        return cls._labels_for_locales(normalized)

    @classmethod
    def _labels_for_locales(cls, locales: Set[str]) -> List[str]:
        labels = list(cls.BASE_LABELS)
        for locale, locale_labels in cls.LOCALE_LABELS.items():
            if locale in locales:
                labels.extend(locale_labels)
        return labels

    def _compile_patterns(self) -> Dict[str, Pattern]:
        patterns: Dict[str, Pattern] = {
            # Email pattern - RFC 5322 subset
            # Intentionally permissive to favor false positives over false negatives
            # Allows for multiple dots, special characters in local part, and subdomains
            # Note: This is broader than the spec to catch more potential emails
            "EMAIL": re.compile(
                r"""
                (?<![A-Za-z0-9._%+\-@])
                (?![A-Za-z_]{2,20}=)
                [A-Za-z0-9!#$%&*+\-/=^_`{|}~]
                [A-Za-z0-9!#$%&'*+\-/=?^_`{|}~.]*
                @
                (?:\.?[A-Za-z0-9-]+\.)+
                [A-Za-z]{2,}
                (?=$|[^A-Za-z])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Phone pattern - North American Numbering Plan (NANP) format
            # Accepts common US and international formats while avoiding IDs/product codes.
            "PHONE": re.compile(
                r"""
                (?<![A-Za-z0-9])
                (?:
                    # US/NANP patterns
                    (?:(?:\+?1)[-\.\s]?)?
                    (?:\(\d{3}\)|\d{3})
                    [-\.\s]?
                    \d{3}
                    [-\.\s]?
                    \d{4}
                    |
                    # International example formats, e.g., +44 20 7946 0958
                    \+\d{1,3}
                    [\s\-\.]?
                    \d{1,4}
                    (?:[\s\-\.]?\d{2,4}){2,3}
                )
                (?![-A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # SSN pattern - U.S. Social Security Number
            # Supports dashed and no-dash formats.
            "SSN": re.compile(
                r"""
                (?<!\d)
                (?:
                    (?!000|666)\d{3}-(?!00)\d{2}-(?!0000)\d{4}
                    |
                    (?!000|666)\d{3}(?!00)\d{2}(?!0000)\d{4}
                )
                (?!\d)
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
            # IP Address pattern - strict IPv4 only.
            "IP_ADDRESS": re.compile(
                r"""
                \b
                (?:
                    (?:25[0-5]|2[0-4]\d|1?\d?\d)\.
                    (?:25[0-5]|2[0-4]\d|1?\d?\d)\.
                    (?:25[0-5]|2[0-4]\d|1?\d?\d)\.
                    (?:25[0-5]|2[0-4]\d|1?\d?\d)
                )
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Date pattern - supports numeric formats, month names, and year-only.
            "DOB": re.compile(
                r"""
                \b
                (?:
                    (?:0?[1-9]|1[0-2])
                    [/-]
                    (?:0?[1-9]|[12][0-9]|3[01])
                    [/-]
                    (?:\d{2}|\d{4})
                    |
                    (?:\d{4})
                    -
                    (?:0?[1-9]|1[0-2])
                    -
                    (?:0?[1-9]|[12][0-9]|3[01])
                    |
                    (?:
                        Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
                        Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?
                    )
                    \s+
                    (?:0?[1-9]|[12][0-9]|3[01])
                    ,\s+
                    (?:19|20)\d{2}
                    |
                    (?:
                        year
                    )
                    \s+
                    (?:19|20)\d{2}
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
            # German VAT ID (USt-IdNr) - DE followed by 9 digits
            "DE_VAT_ID": re.compile(
                r"""
                (?<![A-Za-z0-9])
                DE
                [\s-]?
                \d{9}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German IBAN - DE followed by 20 digits (often grouped)
            "DE_IBAN": re.compile(
                r"""
                (?<![A-Za-z0-9])
                DE
                \d{2}
                (?:\s?\d{4}){4}
                \s?\d{2}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German Tax ID (Steuer-ID) - 11 digits
            "DE_TAX_ID": re.compile(
                r"""
                (?<![A-Za-z0-9])
                (?:[1-9]\d{10}|[1-9]\d\s?\d{3}\s?\d{3}\s?\d{3})
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German Social Security Number (Rentenversicherungsnummer)
            # Format: 2 digits + 6 digits (DOB) + 1 letter + 3 digits
            "DE_SOCIAL_SECURITY_NUMBER": re.compile(
                r"""
                (?<![A-Za-z0-9])
                \d{2}
                \s?
                \d{6}
                \s?
                [A-Z]
                \s?
                \d{3}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German postal code - PLZ prefix followed by 5 digits
            "DE_POSTAL_CODE": re.compile(
                r"""
                (?<![A-Za-z0-9])
                PLZ
                (?:\s*:\s*|\s+)?
                \d{5}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German passport number - 1 letter followed by 8 digits
            "DE_PASSPORT_NUMBER": re.compile(
                rf"""
                (?<![A-Za-z0-9])
                [{self._DE_PASSPORT_PREFIXES}]
                \d{{8}}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German residence permit number - AT followed by 7 digits (context validated)
            "DE_RESIDENCE_PERMIT_NUMBER": re.compile(
                r"""
                (?<![A-Za-z0-9])
                AT
                \d{7}
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
        }

        return {
            label: pattern
            for label, pattern in patterns.items()
            if label in self.active_labels
        }

    def _build_validators(self) -> Dict[str, Callable[[re.Match, str], bool]]:
        validators: Dict[str, Callable[[re.Match, str], bool]] = {}
        if "DE_TAX_ID" in self.active_labels:
            validators["DE_TAX_ID"] = self._validate_de_tax_id
        if "DE_RESIDENCE_PERMIT_NUMBER" in self.active_labels:
            validators["DE_RESIDENCE_PERMIT_NUMBER"] = self._validate_de_residence_permit
        return validators

    @staticmethod
    def _digits_only(value: str) -> str:
        return "".join(ch for ch in value if ch.isdigit())

    @staticmethod
    def _de_tax_id_check_digit(digits10: str) -> int:
        product = 10
        for ch in digits10:
            sum_ = (int(ch) + product) % 10
            if sum_ == 0:
                sum_ = 10
            product = (sum_ * 2) % 11
        return (11 - product) % 10

    def _validate_de_tax_id(self, match: re.Match, text: str) -> bool:
        digits = self._digits_only(match.group())
        if len(digits) != 11:
            return False
        if digits[0] == "0":
            return False
        return digits[-1] == str(self._de_tax_id_check_digit(digits[:10]))

    def _validate_de_residence_permit(self, match: re.Match, text: str) -> bool:
        window = 40
        start = max(match.start() - window, 0)
        end = min(match.end() + window, len(text))
        context = text[start:end]
        return bool(self._DE_RESIDENCE_CONTEXT_RE.search(context))

    @classmethod
    def create(cls, locales: Optional[Iterable[str]] = None) -> "RegexAnnotator":
        """Factory method to create a new RegexAnnotator instance."""
        return cls(locales=locales)

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
            validator = self.validators.get(label)
            for match in pattern.finditer(text):
                if validator and not validator(match, text):
                    continue
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
            validator = self.validators.get(label)
            for match in pattern.finditer(text):
                if validator and not validator(match, text):
                    continue
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
