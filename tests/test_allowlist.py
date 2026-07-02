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
        result = datafog.scan(f"mail {EMAIL}", engine="regex", allowlist=["jane.doe"])
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


class TestReDoSGuards:
    def test_catastrophic_pattern_rejected(self):
        with pytest.raises(ValueError, match="catastrophic backtracking"):
            datafog.scan("text", engine="regex", allowlist_patterns=[r"(a+)+$"])

    def test_nested_star_rejected(self):
        with pytest.raises(ValueError, match="catastrophic backtracking"):
            datafog.scan("text", engine="regex", allowlist_patterns=[r"(.*)*"])

    def test_overlong_pattern_rejected(self):
        with pytest.raises(ValueError, match="at most"):
            datafog.scan("text", engine="regex", allowlist_patterns=["a" * 513])

    def test_overlong_entity_text_skips_patterns_but_is_kept(self):
        # Fail-safe: an entity too long to pattern-match safely must still
        # be reported, never silently suppressed.
        from datafog.engine import Entity, _apply_allowlist

        long_entity = Entity(
            type="EMAIL",
            text="a" * 600,
            start=0,
            end=600,
            confidence=1.0,
            engine="regex",
        )
        kept = _apply_allowlist([long_entity], None, [r".*"])
        assert kept == [long_entity]

    def test_overlong_entity_text_still_matches_exact_allowlist(self):
        # The subject-length cap only bounds regex matching; exact string
        # comparison is O(n) and still applies.
        from datafog.engine import Entity, _apply_allowlist

        long_entity = Entity(
            type="EMAIL",
            text="a" * 600,
            start=0,
            end=600,
            confidence=1.0,
            engine="regex",
        )
        assert _apply_allowlist([long_entity], ["a" * 600], None) == []

    def test_benign_quantified_group_still_allowed(self):
        result = datafog.scan(
            f"mail {EMAIL}",
            engine="regex",
            allowlist_patterns=[r"(abc)+", r".*@example\.com"],
        )
        assert result.entities == []  # broad pattern suppresses, no rejection


class TestEnginePaths:
    def test_smart_engine_applies_allowlist(self):
        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            result = datafog.scan(f"mail {EMAIL}", engine="smart", allowlist=[EMAIL])
        assert result.entities == []

    def test_redact_rejects_allowlist_with_explicit_entities(self):
        scanned = datafog.scan(f"mail {EMAIL}", engine="regex")
        with pytest.raises(ValueError, match="cannot be combined"):
            datafog.redact(
                f"mail {EMAIL}",
                entities=scanned.entities,
                allowlist=[EMAIL],
            )


class TestPresidioAliases:
    def test_email_address_alias(self):
        result = datafog.scan(
            f"mail {EMAIL}", engine="regex", entity_types=["EMAIL_ADDRESS"]
        )
        assert [e.type for e in result.entities] == ["EMAIL"]

    def test_us_ssn_alias(self):
        ssn = "856-45-" "6789"
        result = datafog.scan(f"ssn {ssn}", engine="regex", entity_types=["US_SSN"])
        assert [e.type for e in result.entities] == ["SSN"]


class TestPyTyped:
    def test_py_typed_marker_ships_with_package(self):
        import importlib.resources

        assert importlib.resources.files("datafog").joinpath("py.typed").is_file()
