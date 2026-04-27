from __future__ import annotations

import base64
import binascii
import ipaddress
import re
import uuid
from datetime import datetime
from typing import Dict, List, Pattern, Tuple
from urllib.parse import urlparse

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
    LABELS = [
        "EMAIL",
        "PHONE",
        "SSN",
        "CREDIT_CARD",
        "IP_ADDRESS",
        "DATE_OF_BIRTH",
        "DOB",
        "ZIP",
        "URL",
        "UUID",
        "API_KEY",
        "SECRET",
        "ACCESS_TOKEN",
        "PRIVATE_KEY",
        "PASSWORD",
        "JWT",
        "BEARER_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "HUGGINGFACE_TOKEN",
        "COHERE_API_KEY",
        "MISTRAL_API_KEY",
        "GROQ_API_KEY",
        "TOGETHER_API_KEY",
        "PERPLEXITY_API_KEY",
        "XAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "SLACK_TOKEN",
        "STRIPE_KEY",
    ]

    _DATE_VALUE_PATTERN = r"""
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
    """

    _SECRET_PLACEHOLDERS = {
        "changeme",
        "example",
        "none",
        "null",
        "password",
        "placeholder",
        "secret",
        "test",
        "token",
        "your-api-key",
        "your_api_key",
        "your_key_here",
        "your-token",
        "your_token",
    }

    def __init__(self):
        # Compile all patterns once at initialization
        self.patterns: Dict[str, Pattern] = {
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
            # Contextual date of birth pattern. Generic dates stay DATE/P1 in v5.
            "DATE_OF_BIRTH": re.compile(
                rf"""
                \b
                (?:
                    dob
                    |
                    d\.o\.b\.?
                    |
                    date\s+of\s+birth
                    |
                    birth(?:day|date)?
                    |
                    born
                )
                \b
                \s*
                (?:
                    (?::|=)
                    |
                    is\b
                    |
                    on\b
                )?
                \s*
                (?P<value>{self._DATE_VALUE_PATTERN})
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            # Date pattern - supports numeric formats, month names, and year-only.
            "DOB": re.compile(
                rf"""
                \b
                {self._DATE_VALUE_PATTERN}
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
            "URL": re.compile(
                r"""
                (?<![A-Za-z0-9])
                (?:
                    https?://[^\s<>"')]+
                    |
                    www\.[^\s<>"')]+
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "UUID": re.compile(
                r"""
                \b
                [0-9a-f]{8}
                -
                [0-9a-f]{4}
                -
                [1-5][0-9a-f]{3}
                -
                [89ab][0-9a-f]{3}
                -
                [0-9a-f]{12}
                \b
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "JWT": re.compile(
                r"""
                \b
                eyJ[A-Za-z0-9_-]{10,}
                \.
                [A-Za-z0-9_-]{10,}
                \.
                [A-Za-z0-9_-]{10,}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "BEARER_TOKEN": re.compile(
                r"""
                \bBearer
                \s+
                (?P<value>[A-Za-z0-9._~+/=-]{20,})
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "AWS_ACCESS_KEY_ID": re.compile(
                r"""
                \b
                (?:AKIA|ASIA)
                [0-9A-Z]{16}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "GITHUB_TOKEN": re.compile(
                r"""
                \b
                (?:
                    (?:ghp|gho|ghu|ghs|ghr)_
                    [A-Za-z0-9_]{36,255}
                    |
                    github_pat_
                    [A-Za-z0-9_]{22,255}
                )
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "OPENAI_API_KEY": re.compile(
                r"""
                \b
                sk-
                (?:proj-)?
                [A-Za-z0-9_-]{20,}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "ANTHROPIC_API_KEY": re.compile(
                r"""
                \b
                sk-ant-api\d{2}-
                [A-Za-z0-9_-]{20,}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "GOOGLE_API_KEY": re.compile(
                r"""
                \b
                (?:
                    AIza[0-9A-Za-z_\-]{35}
                    \b
                    |
                    (?:
                        google|gemini|generative[_-]?language
                    )
                    [_-]?
                    api[_-]?key
                    \s*
                    (?::|=)
                    \s*
                    ["']?
                    (?P<value>[A-Za-z0-9_\-]{24,})
                    ["']?
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "HUGGINGFACE_TOKEN": re.compile(
                r"""
                \b
                (?:
                    hf_[A-Za-z0-9]{20,}
                    \b
                    |
                    (?:
                        hf|hugging[_-]?face|huggingfacehub
                    )
                    [_-]?
                    (?:api[_-]?key|token)
                    \s*
                    (?::|=)
                    \s*
                    ["']?
                    (?P<value>[A-Za-z0-9_.\-]{20,})
                    ["']?
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "COHERE_API_KEY": re.compile(
                r"""
                \b
                cohere
                [_-]?
                api[_-]?key
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9_.\-]{20,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "MISTRAL_API_KEY": re.compile(
                r"""
                \b
                mistral
                [_-]?
                api[_-]?key
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9_.\-]{20,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "GROQ_API_KEY": re.compile(
                r"""
                \b
                (?:
                    gsk_[A-Za-z0-9]{20,}
                    \b
                    |
                    groq
                    [_-]?
                    api[_-]?key
                    \s*
                    (?::|=)
                    \s*
                    ["']?
                    (?P<value>[A-Za-z0-9_.\-]{20,})
                    ["']?
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "TOGETHER_API_KEY": re.compile(
                r"""
                \b
                together
                [_-]?
                api[_-]?key
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9_.\-]{20,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "PERPLEXITY_API_KEY": re.compile(
                r"""
                \b
                (?:
                    pplx-[A-Za-z0-9]{20,}
                    \b
                    |
                    perplexity
                    [_-]?
                    api[_-]?key
                    \s*
                    (?::|=)
                    \s*
                    ["']?
                    (?P<value>[A-Za-z0-9_.\-]{20,})
                    ["']?
                )
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "XAI_API_KEY": re.compile(
                r"""
                \b
                xai
                [_-]?
                api[_-]?key
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9_.\-]{20,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "AZURE_OPENAI_API_KEY": re.compile(
                r"""
                \b
                azure
                [_-]?
                openai
                [_-]?
                api[_-]?key
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9_.\-]{20,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "SLACK_TOKEN": re.compile(
                r"""
                \b
                (?:xox[baprs]|xapp|xwfp)-
                [A-Za-z0-9-]{10,}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "STRIPE_KEY": re.compile(
                r"""
                \b
                (?:sk|pk|rk)_
                (?:live|test)_
                [A-Za-z0-9]{16,}
                \b
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "PRIVATE_KEY": re.compile(
                r"""
                -----BEGIN\s+
                (?:
                    RSA\s+|
                    EC\s+|
                    OPENSSH\s+|
                    DSA\s+
                )?
                PRIVATE\s+KEY-----
                [\s\S]+?
                -----END\s+
                (?:
                    RSA\s+|
                    EC\s+|
                    OPENSSH\s+|
                    DSA\s+
                )?
                PRIVATE\s+KEY-----
                """,
                re.MULTILINE | re.VERBOSE,
            ),
            "API_KEY": re.compile(
                r"""
                \b
                (?:api[_-]?key|secret[_-]?key)
                \b
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9][A-Za-z0-9_.\-]{19,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "ACCESS_TOKEN": re.compile(
                r"""
                \b
                (?:access[_-]?token|auth[_-]?token|id[_-]?token|refresh[_-]?token)
                \b
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9][A-Za-z0-9_.\-]{19,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "SECRET": re.compile(
                r"""
                \b
                (?:client[_-]?secret|webhook[_-]?secret|secret)
                \b
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[A-Za-z0-9][A-Za-z0-9_.\-]{15,})
                ["']?
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            "PASSWORD": re.compile(
                r"""
                \b
                (?:password|passwd|pwd)
                \b
                \s*
                (?::|=)
                \s*
                ["']?
                (?P<value>[^\s"',;]{8,})
                ["']?
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
                match_text = self._match_text(match)
                if self._is_valid_match(label, match_text):
                    result[label].append(match_text)

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
                start, end, match_text = self._match_span(match)
                if not self._is_valid_match(label, match_text):
                    continue
                span = Span(
                    label=label,
                    start=start,
                    end=end,
                    text=match_text,
                )
                spans_by_label[label].append(span)
                all_spans.append(span)

        regex_result = {
            lbl: [s.text for s in spans_by_label[lbl]] for lbl in spans_by_label
        }

        return regex_result, AnnotationResult(text=text, spans=all_spans)

    @staticmethod
    def _match_span(match: re.Match) -> Tuple[int, int, str]:
        if "value" in match.re.groupindex and match.group("value") is not None:
            return match.start("value"), match.end("value"), match.group("value")
        return match.start(), match.end(), match.group()

    @classmethod
    def _match_text(cls, match: re.Match) -> str:
        return cls._match_span(match)[2]

    @classmethod
    def _is_valid_match(cls, label: str, value: str) -> bool:
        validator = {
            "EMAIL": cls._valid_email,
            "PHONE": cls._valid_phone,
            "SSN": cls._valid_ssn,
            "CREDIT_CARD": cls._valid_credit_card,
            "IP_ADDRESS": cls._valid_ip_address,
            "DOB": cls._valid_date,
            "DATE_OF_BIRTH": cls._valid_date,
            "ZIP": cls._valid_zip,
            "URL": cls._valid_url,
            "UUID": cls._valid_uuid,
            "JWT": cls._valid_jwt,
            "API_KEY": cls._valid_secret_value,
            "ACCESS_TOKEN": cls._valid_secret_value,
            "SECRET": cls._valid_secret_value,
            "BEARER_TOKEN": cls._valid_secret_value,
            "PASSWORD": cls._valid_password,
            "OPENAI_API_KEY": cls._valid_secret_value,
            "ANTHROPIC_API_KEY": cls._valid_secret_value,
            "GOOGLE_API_KEY": cls._valid_secret_value,
            "HUGGINGFACE_TOKEN": cls._valid_secret_value,
            "COHERE_API_KEY": cls._valid_secret_value,
            "MISTRAL_API_KEY": cls._valid_secret_value,
            "GROQ_API_KEY": cls._valid_secret_value,
            "TOGETHER_API_KEY": cls._valid_secret_value,
            "PERPLEXITY_API_KEY": cls._valid_secret_value,
            "XAI_API_KEY": cls._valid_secret_value,
            "AZURE_OPENAI_API_KEY": cls._valid_secret_value,
        }.get(label)
        if validator is None:
            return True
        return validator(value)

    @staticmethod
    def _valid_email(value: str) -> bool:
        if value.count("@") != 1:
            return False
        local, domain = value.rsplit("@", 1)
        if not local or not domain or "[" in domain or "]" in domain:
            return False
        if ".." in local or ".." in domain:
            return False
        labels = [label for label in domain.lstrip(".").split(".") if label]
        if len(labels) < 2:
            return False
        for label in labels:
            if label.startswith("-") or label.endswith("-"):
                return False
        return labels[-1].isalpha() and len(labels[-1]) >= 2

    @staticmethod
    def _valid_phone(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        if value.strip().startswith("+"):
            return 8 <= len(digits) <= 15
        return len(digits) in {10, 11} and (len(digits) == 10 or digits.startswith("1"))

    @staticmethod
    def _valid_ssn(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 9:
            return False
        area, group, serial = digits[:3], digits[3:5], digits[5:]
        if area in {"000", "666"} or group == "00" or serial == "0000":
            return False
        return digits != "078051120"

    @classmethod
    def _valid_credit_card(cls, value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        return 13 <= len(digits) <= 19 and cls._passes_luhn(digits)

    @staticmethod
    def _passes_luhn(digits: str) -> bool:
        total = 0
        parity = len(digits) % 2
        for index, char in enumerate(digits):
            number = int(char)
            if index % 2 == parity:
                number *= 2
                if number > 9:
                    number -= 9
            total += number
        return total % 10 == 0

    @staticmethod
    def _valid_ip_address(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _valid_date(value: str) -> bool:
        normalized = value.strip()
        if normalized.lower().startswith("year "):
            year = normalized.split()[-1]
            return year.isdigit() and 1900 <= int(year) <= 2099
        for date_format in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y-%m-%d"):
            try:
                datetime.strptime(normalized, date_format)
                return True
            except ValueError:
                pass
        for date_format in ("%B %d, %Y", "%b %d, %Y"):
            try:
                datetime.strptime(normalized, date_format)
                return True
            except ValueError:
                pass
        return False

    @staticmethod
    def _valid_zip(value: str) -> bool:
        return re.fullmatch(r"\d{5}(?:-\d{4})?", value) is not None

    @staticmethod
    def _valid_url(value: str) -> bool:
        candidate = value if "://" in value else f"https://{value}"
        parsed = urlparse(candidate)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not host:
            return False
        if "." not in host and host != "localhost":
            return False
        return all(part for part in host.split("."))

    @staticmethod
    def _valid_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
        except ValueError:
            return False
        return True

    @classmethod
    def _valid_jwt(cls, value: str) -> bool:
        parts = value.split(".")
        if len(parts) != 3:
            return False
        try:
            header = cls._decode_base64url(parts[0])
            payload = cls._decode_base64url(parts[1])
        except (binascii.Error, ValueError):
            return False
        return header.startswith(b"{") and payload.startswith(b"{")

    @staticmethod
    def _decode_base64url(value: str) -> bytes:
        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii"))

    @classmethod
    def _valid_secret_value(cls, value: str) -> bool:
        normalized = value.strip().strip("\"'")
        if len(normalized) < 16:
            return False
        if normalized.lower() in cls._SECRET_PLACEHOLDERS:
            return False
        if len(set(normalized)) < 3:
            return False
        return any(char.isalnum() for char in normalized)

    @classmethod
    def _valid_password(cls, value: str) -> bool:
        normalized = value.strip().strip("\"'")
        if len(normalized) < 8:
            return False
        if normalized.lower() in cls._SECRET_PLACEHOLDERS:
            return False
        return len(set(normalized)) >= 4
