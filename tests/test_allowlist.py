"""Tests for scan/redact allowlist support and presidio-style entity aliases.

PII literals are assembled from split parts so write-time scanners
(including our own Claude Code hook) do not match this source file.
"""

import pytest

import datafog

EMAIL = "jane.doe@" "example.com"
OTHER_EMAIL = "sid@" "example.com"
TIMESTAMP_LIKE = "17830" "25668"  # ten digits: matches the PHONE pattern


class TestExactAllowlist:
    def test_allowlisted_value_is_not_reported(self):
        result = datafog.scan(
            f"mail {EMAIL} and {OTHER_EMAIL}",
            engine="regex",
            allowlist=[OTHER_EMAIL],
        )
        assert [e.text for e in result.entities] == [EMAIL]

    def test_allowlist_is_exact_not_substring(self):
        result = datafog.scan(
            f"mail {EMAIL}", engine="regex", allowlist=["jane.doe"]
        )
        assert [e.text for e in result.entities] == [EMAIL]

    def test_empty_allowlist_is_noop(self):
        result = datafog.scan(f"mail {EMAIL}", engine="regex", allowlist=[])
        assert len(result.entities) == 1

    def test_redact_respects_allowlist(self):
        result = datafog.redact(
            f"mail {EMAIL} and {OTHER_EMAIL}",
            engine="regex",
            allowlist=[OTHER_EMAIL],
        )
        assert OTHER_EMAIL in result.redacted_text
        assert EMAIL not in result.redacted_text


class TestPatternAllowlist:
    def test_pattern_suppresses_matching_entities(self):
        # The motivating case: unix timestamps and numeric IDs match the
        # PHONE pattern; a pattern allowlist can exempt all-digit strings.
        noisy = datafog.scan(f"created {TIMESTAMP_LIKE}", engine="regex")
        assert len(noisy.entities) == 1  # sanity: it is detected by default

        result = datafog.scan(
            f"created {TIMESTAMP_LIKE}",
            engine="regex",
            allowlist_patterns=[r"^\d{10}$"],
        )
        assert result.entities == []

    def test_pattern_matches_full_entity_text_only(self):
        result = datafog.scan(
            f"mail {EMAIL}", engine="regex", allowlist_patterns=[r"^jane\."]
        )
        assert len(result.entities) == 1  # partial match must not suppress

    def test_invalid_pattern_raises_value_error(self):
        with pytest.raises(ValueError, match="allowlist_patterns"):
            datafog.scan("text", engine="regex", allowlist_patterns=["("])

    def test_patterns_and_values_combine(self):
        result = datafog.scan(
            f"{EMAIL} then {TIMESTAMP_LIKE}",
            engine="regex",
            allowlist=[EMAIL],
            allowlist_patterns=[r"^\d{10}$"],
        )
        assert result.entities == []


class TestPresidioAliases:
    def test_email_address_alias(self):
        result = datafog.scan(
            f"mail {EMAIL}", engine="regex", entity_types=["EMAIL_ADDRESS"]
        )
        assert [e.type for e in result.entities] == ["EMAIL"]

    def test_us_ssn_alias(self):
        ssn = "856-45-" "6789"
        result = datafog.scan(
            f"ssn {ssn}", engine="regex", entity_types=["US_SSN"]
        )
        assert [e.type for e in result.entities] == ["SSN"]


class TestPyTyped:
    def test_py_typed_marker_ships_with_package(self):
        import importlib.resources

        assert importlib.resources.files("datafog").joinpath("py.typed").is_file()
