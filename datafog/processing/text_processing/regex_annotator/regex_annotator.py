import re
from collections.abc import Iterable
from typing import Dict, List, Match, Pattern, Tuple

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

    BASE_LABELS = ["EMAIL", "PHONE", "SSN", "CREDIT_CARD", "IP_ADDRESS", "DOB", "ZIP"]
    GERMAN_LABELS = [
        "DE_VAT_ID",
        "DE_IBAN",
        "DE_TAX_ID",
        "DE_SOCIAL_SECURITY_NUMBER",
        "DE_POSTAL_CODE",
        "DE_PASSPORT_NUMBER",
        "DE_RESIDENCE_PERMIT_NUMBER",
    ]
    LABELS = BASE_LABELS + GERMAN_LABELS
    DEFAULT_LABELS = BASE_LABELS
    SUPPORTED_LOCALES = {"de", "de-de", "de_de"}
    LOCALE_LABELS = {
        "de": GERMAN_LABELS,
        "de-de": GERMAN_LABELS,
        "de_de": GERMAN_LABELS,
    }

    @staticmethod
    def _phone_pattern(strict_numeric: bool) -> "Pattern":
        # Strict (default): a separator, parentheses, or a +country prefix is
        # required, so a bare ten-digit run (tab/row ids, timestamps) is not
        # matched (issue #158). Structural NANP validation (area/exchange must
        # start 2-9) is deferred to the DFPY-110 validator layer.
        bare = "" if strict_numeric else r"| (?:\+?1[-.\s]?)? \d{3} \d{3} \d{4}"
        return re.compile(
            r"""
            (?<![A-Za-z0-9])
            (?:
                # Parenthesized area code (separators optional afterwards)
                (?:(?:\+?1)[-.\s]?)?
                \(\d{3}\) [-.\s]? \d{3} [-.\s]? \d{4}
                |
                # Bare area code but a separator between groups is required
                (?:(?:\+?1)[-.\s]?)?
                \d{3} [-.\s] \d{3} [-.\s] \d{4}
                |
                # International formats, e.g. a +country prefixed number
                \+\d{1,3} [\s\-.]? \d{1,4} (?:[\s\-.]?\d{2,4}){2,3}
                BARE
            )
            (?![-A-Za-z0-9])
            """.replace(
                "BARE", bare
            ),
            re.IGNORECASE | re.MULTILINE | re.VERBOSE,
        )

    @staticmethod
    def _ssn_pattern(strict_numeric: bool) -> "Pattern":
        # Strict (default): a dash or space delimiter is required, so a bare
        # nine-digit run is not treated as an SSN (issue #158). Area != 000/666,
        # group != 00, serial != 0000 as before; broader SSA range checks are
        # deferred to the DFPY-110 validator layer. Opt in to bare matching
        # with strict_numeric=False for v4.4.0 parity.
        bare = "" if strict_numeric else r"| (?!000|666)\d{3}(?!00)\d{2}(?!0000)\d{4}"
        return re.compile(
            r"""
            (?<!\d)
            (?:
                (?!000|666)\d{3}[-\s](?!00)\d{2}[-\s](?!0000)\d{4}
                BARE
            )
            (?!\d)
            """.replace(
                "BARE", bare
            ),
            re.IGNORECASE | re.MULTILINE | re.VERBOSE,
        )

    def __init__(
        self,
        locales: str | Iterable[str] | None = None,
        enabled_labels: Iterable[str] | None = None,
        strict_numeric: bool = True,
    ):
        # When strict_numeric is True (default), SSN requires delimiters and
        # PHONE requires formatting cues, so bare digit runs (tab ids, row
        # ids, timestamps) do not match. Set False to also accept undelimited
        # nine-digit SSNs and bare ten-digit phone numbers (issue #158).
        self.strict_numeric = strict_numeric
        self.locales = self._normalize_locales(locales)
        self.active_labels = self.active_labels_for(self.locales, enabled_labels)

        # Compile all patterns once at initialization
        all_patterns: Dict[str, Pattern] = {
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
            # Phone pattern - North American Numbering Plan (NANP) format.
            # Area code and exchange must start 2-9. In strict mode
            # (default) a bare ten-digit run is not matched; a separator,
            # parentheses, or a +country prefix is required (issue #158).
            "PHONE": self._phone_pattern(strict_numeric),
            # SSN pattern - U.S. Social Security Number
            # Supports dashed and no-dash formats.
            # Note: overlaps with locale-gated labels (e.g. the nine-digit run
            # inside a DE_VAT_ID) are resolved by the engine's span-overlap
            # suppression, not here, so default (EN) detection keeps v4.4.0
            # behavior even when German labels are active.
            "SSN": self._ssn_pattern(strict_numeric),
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
            # German VAT ID (USt-IdNr) - DE followed by 9 digits.
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
            # German IBAN - DE followed by 20 digits, often grouped.
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
            # German Tax ID (Steuer-ID) - context required to avoid generic IDs.
            "DE_TAX_ID": re.compile(
                r"""
                (?:
                    Steuer[\s-]?ID |
                    Steueridentifikationsnummer |
                    Identifikationsnummer |
                    IdNr\.? |
                    Tax[\s-]?ID
                )
                \s*[:#-]?\s*
                (?P<value>
                    (?<![A-Za-z0-9])
                    (?:\d{11}|\d{2}\s?\d{3}\s?\d{3}\s?\d{3})
                    (?![A-Za-z0-9])
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German pension insurance number (Rentenversicherungsnummer).
            "DE_SOCIAL_SECURITY_NUMBER": re.compile(
                r"""
                (?:
                    Rentenversicherungsnummer |
                    Sozialversicherungsnummer |
                    RVNR |
                    SVNR
                )
                \s*[:#-]?\s*
                (?P<value>
                    (?<![A-Za-z0-9])
                    \d{2}
                    \s?
                    \d{6}
                    \s?
                    [A-Z]
                    \s?
                    \d{3}
                    (?![A-Za-z0-9])
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German postal code with an explicit German/PLZ prefix.
            "DE_POSTAL_CODE": re.compile(
                r"""
                (?<![A-Za-z0-9])
                (?P<value>
                    (?:
                        PLZ[\s:-]? |
                        DE[\s-] |
                        D[\s-]
                    )
                    \d{5}
                )
                (?![A-Za-z0-9])
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German passport number - context required; bare A12345678 is too broad.
            "DE_PASSPORT_NUMBER": re.compile(
                r"""
                (?:
                    Passnummer |
                    Reisepass(?:nummer)? |
                    Passport(?:\s+No\.?|\s+Number)?
                )
                \s*[:#-]?\s*
                (?P<value>
                    (?<![A-Za-z0-9])
                    [A-Z]
                    \d{8}
                    (?![A-Za-z0-9])
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # German residence permit number - context required; AT IDs are common.
            "DE_RESIDENCE_PERMIT_NUMBER": re.compile(
                r"""
                (?:
                    Aufenthaltstitel |
                    Aufenthaltserlaubnis |
                    Residence\s+Permit |
                    eAT
                )
                \s*[:#-]?\s*
                (?P<value>
                    (?<![A-Za-z0-9])
                    AT
                    \d{7}
                    (?![A-Za-z0-9])
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
        }
        self.patterns = {
            label: pattern
            for label, pattern in all_patterns.items()
            if label in self.active_labels
        }

    @classmethod
    def _normalize_locales(cls, locales: str | Iterable[str] | None) -> tuple[str, ...]:
        if locales is None:
            return ()
        if isinstance(locales, str):
            locales = [locales]
        normalized = []
        for locale in locales:
            value = locale.strip().lower()
            if not value:
                continue
            if value not in cls.SUPPORTED_LOCALES:
                allowed = ", ".join(sorted(cls.SUPPORTED_LOCALES))
                raise ValueError(f"locale must be one of: {allowed}")
            normalized.append(value)
        return tuple(dict.fromkeys(normalized))

    @classmethod
    def active_labels_for(
        cls,
        locales: str | Iterable[str] | None = None,
        enabled_labels: Iterable[str] | None = None,
    ) -> list[str]:
        """Resolve the labels active for the given locales and explicit labels."""
        active = set(cls.DEFAULT_LABELS)
        for locale in cls._normalize_locales(locales):
            active.update(cls.LOCALE_LABELS[locale])
        if enabled_labels is not None:
            active.update(label.strip().upper() for label in enabled_labels)
        return [label for label in cls.LABELS if label in active]

    @staticmethod
    def _match_text(match: Match[str]) -> str:
        return match.groupdict().get("value") or match.group()

    @staticmethod
    def _match_span(match: Match[str]) -> tuple[int, int]:
        if "value" in match.groupdict() and match.group("value") is not None:
            return match.start("value"), match.end("value")
        return match.start(), match.end()

    @classmethod
    def create(cls, **kwargs) -> "RegexAnnotator":
        """Factory method to create a new RegexAnnotator instance."""
        return cls(**kwargs)

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
                result[label].append(self._match_text(match))

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
                start, end = self._match_span(match)
                span = Span(
                    label=label,
                    start=start,
                    end=end,
                    text=self._match_text(match),
                )
                spans_by_label[label].append(span)
                all_spans.append(span)

        regex_result = {
            lbl: [s.text for s in spans_by_label[lbl]] for lbl in spans_by_label
        }

        return regex_result, AnnotationResult(text=text, spans=all_spans)
