"""Behavioral coverage for the opt-in native detection adapter."""

import builtins
import sys
from types import SimpleNamespace

import pytest

from datafog import engine
from tests.test_core_capability_adapter import capability_fixture


def finding(label, text, start, end):
    return SimpleNamespace(
        entity_type=label,
        matched_text=text,
        codepoint_range=SimpleNamespace(start=start, end=end),
        byte_range=SimpleNamespace(start=999, end=1000),
    )


@pytest.fixture
def native(monkeypatch):
    calls = []
    findings = []

    def scan(text, config=None):
        calls.append(text)
        return findings

    monkeypatch.setitem(
        sys.modules,
        "datafog_core",
        SimpleNamespace(scan=scan, capabilities=capability_fixture),
    )
    return findings, calls


def test_native_offsets_duplicates_order_and_provenance(native):
    findings, calls = native
    text = "😀 alice@example.com / alice@example.com"
    findings.extend(
        [
            finding("EMAIL", "alice@example.com", 22, 39),
            finding("EMAIL", "alice@example.com", 2, 19),
        ]
    )
    result = engine.scan(text, engine="regex", backend="rust")
    assert calls == [text]
    assert result.text == text
    assert result.engine_used == "regex"
    assert [item.start for item in result.entities] == [2, 22]
    assert all(text[item.start : item.end] == item.text for item in result.entities)
    assert all(
        item.engine == "regex" and item.confidence == 1.0 for item in result.entities
    )


@pytest.mark.parametrize("selection", [None, [], [" email_address "]])
def test_selection_alias_and_empty_selection(native, selection):
    findings, _ = native
    findings.append(finding("EMAIL", "a@example.com", 0, 13))
    result = engine.scan(
        "a@example.com", "regex", entity_types=selection, backend="rust"
    )
    assert len(result.entities) == 1


def test_unknown_selection_preserves_legacy_empty_result(native):
    findings, _ = native
    findings.append(finding("EMAIL", "a@example.com", 0, 13))
    assert (
        engine.scan(
            "a@example.com", "regex", entity_types=["UNKNOWN"], backend="rust"
        ).entities
        == []
    )


def test_unknown_native_label_preserved_without_silently_dropping_pii(native):
    findings, _ = native
    findings.append(finding("FUTURE_LABEL", "example", 0, 7))
    result = engine.scan("example", "regex", backend="rust")
    assert [item.type for item in result.entities] == ["FUTURE_LABEL"]


def test_python_overlap_priority_precedes_selection(native):
    findings, _ = native
    text = "1234567890123456"
    findings.extend(
        [finding("PHONE", text[:10], 0, 10), finding("CREDIT_CARD", text, 0, 16)]
    )
    result = engine.scan(text, "regex", backend="rust")
    assert [item.type for item in result.entities] == ["CREDIT_CARD"]
    assert (
        engine.scan(text, "regex", entity_types=["PHONE"], backend="rust").entities
        == []
    )


@pytest.mark.parametrize(
    "kwargs, count",
    [
        ({"allowlist": ["a@example.com"]}, 0),
        ({"allowlist": ["A@example.com"]}, 1),
        ({"allowlist_patterns": [r"(?=a@).*\.com"]}, 0),
        ({"allowlist_patterns": ["example"]}, 1),
    ],
)
def test_python_allowlist_semantics(native, kwargs, count):
    findings, _ = native
    findings.append(finding("EMAIL", "a@example.com", 0, 13))
    assert (
        len(engine.scan("a@example.com", "regex", backend="rust", **kwargs).entities)
        == count
    )


@pytest.mark.parametrize("pattern", ["[", "(a+)+", "x" * 513])
def test_allowlist_validation_before_native(native, pattern):
    _, calls = native
    with pytest.raises(ValueError):
        engine.scan("", "regex", backend="rust", allowlist_patterns=[pattern])
    assert not calls


@pytest.mark.parametrize("locale", [["de"], [" DE-DE "], "de_de"])
def test_advertised_german_locales_accepted(native, locale):
    _, calls = native
    assert not engine.scan("", "regex", locales=locale, backend="rust").entities
    assert calls == [""]


def test_german_selection_is_filtered_after_native_detection(native):
    findings, _ = native
    findings.append(finding("DE_IBAN", "DE-example", 0, 10))
    result = engine.scan(
        "DE-example", "regex", entity_types=["de_iban"], backend="rust"
    )
    assert [item.type for item in result.entities] == ["DE_IBAN"]


def test_unknown_locale_validation_preserved(native):
    with pytest.raises(ValueError, match="locale"):
        engine.scan("", "regex", locales=["unsupported"], backend="rust")


@pytest.mark.parametrize("name", ["smart", "spacy", "gliner"])
def test_nonregex_engine_rejected(native, name):
    _, calls = native
    with pytest.raises(ValueError, match="only engine='regex'"):
        engine.scan("", name, backend="rust")
    assert not calls


def test_bad_backend_rejected():
    with pytest.raises(ValueError, match="backend must be one of"):
        engine.scan("", "regex", backend="auto")


def test_no_native_import_on_python_path_and_actionable_missing_error(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "datafog_core":
            raise ModuleNotFoundError("native absent", name=name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    assert engine.scan("a@example.com", "regex").entities
    with pytest.raises(ImportError, match=r'pip install "datafog\[rust\]"'):
        engine.scan("a@example.com", "regex", backend="rust")


def test_native_failure_propagates_without_fallback(monkeypatch):
    error = RuntimeError("native failure")

    def fail(text, config=None):
        raise error

    monkeypatch.setitem(
        sys.modules,
        "datafog_core",
        SimpleNamespace(scan=fail, capabilities=capability_fixture),
    )
    with pytest.raises(RuntimeError) as caught:
        engine.scan("a@example.com", "regex", backend="rust")
    assert caught.value is error


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_all_legacy_transformations_use_native_findings(native, strategy):
    findings, calls = native
    text = "a@example.com a@example.com"
    findings.extend(
        [
            finding("EMAIL", "a@example.com", 0, 13),
            finding("EMAIL", "a@example.com", 14, 27),
        ]
    )
    expected = engine.scan_and_redact(text, "regex", strategy=strategy)
    actual = engine.scan_and_redact(text, "regex", strategy=strategy, backend="rust")
    assert actual == expected
    assert calls == [text]


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_real_native_unicode_and_transformations(strategy):
    pytest.importorskip("datafog_core")
    text = "😀 München a@example.com and a@example.com"
    python_result = engine.scan_and_redact(text, "regex", strategy=strategy)
    native_result = engine.scan_and_redact(
        text, "regex", strategy=strategy, backend="rust"
    )
    assert native_result == python_result
