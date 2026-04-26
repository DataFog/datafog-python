"""Tests for v4.4 bridge APIs that preview the v5 surface."""

from __future__ import annotations

import importlib
import warnings

import pytest

import datafog


def test_top_level_scan_is_available_without_optional_extras() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = datafog.scan("Email jane@example.com")

    assert result.engine_used == "regex"
    assert any(entity.type == "EMAIL" for entity in result.entities)
    assert not captured


def test_top_level_redact_scans_by_default() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = datafog.redact("Email jane@example.com")

    assert result.redacted_text != "Email jane@example.com"
    assert "[EMAIL_1]" in result.redacted_text
    assert result.mapping
    assert not captured


def test_top_level_redact_accepts_precomputed_entities() -> None:
    text = "Email jane@example.com"
    scan_result = datafog.scan(text, engine="regex")

    result = datafog.redact(text, entities=scan_result.entities, strategy="mask")

    assert "jane@example.com" not in result.redacted_text
    assert "*" in result.redacted_text


def test_top_level_redact_supports_preview_presets() -> None:
    result = datafog.redact("Email jane@example.com", preset="llm")

    assert "[EMAIL_1]" in result.redacted_text


def test_top_level_protect_returns_guardrail() -> None:
    guardrail = datafog.protect(on_detect="redact")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        filtered = guardrail.filter("Email jane@example.com")

    assert filtered.redacted_text != "Email jane@example.com"
    assert not captured


def test_legacy_detect_warns_with_replacement() -> None:
    with pytest.warns(FutureWarning, match=r"Use datafog\.scan\(\) instead"):
        result = datafog.detect("Email jane@example.com")

    assert result


def test_legacy_process_warns_with_replacement() -> None:
    with pytest.warns(FutureWarning, match=r"datafog\.scan\(\) or datafog\.redact\(\)"):
        result = datafog.process("Email jane@example.com", anonymize=True)

    assert result["anonymized"] != result["original"]


def test_import_does_not_emit_migration_warnings() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        importlib.reload(datafog)

    assert not [
        warning for warning in captured if issubclass(warning.category, FutureWarning)
    ]
