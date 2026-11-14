"""Backend resolution: native by default, Python fallback, env override."""

import builtins

import pytest

import datafog
from datafog import engine
from datafog.exceptions import CoreUnavailableWarning


@pytest.fixture
def without_core(monkeypatch):
    """Hide ``datafog_core`` from the import machinery."""
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "datafog_core" or name.startswith("datafog_core."):
            raise ImportError("hidden for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__("sys").modules, "datafog_core", raising=False)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(engine, "_cnn_cache", None)


def test_auto_resolves_to_native_when_core_is_installed():
    pytest.importorskip("datafog_core")
    assert engine.resolve_backend(None, "regex") == "rust"


def test_auto_resolves_to_python_without_core(without_core):
    assert engine.resolve_backend(None, "regex") == "python"


def test_auto_keeps_non_regex_engines_on_python():
    pytest.importorskip("datafog_core")
    for engine_name in ("smart", "spacy", "gliner"):
        assert engine.resolve_backend(None, engine_name) == "python"


def test_python_fallback_warns_once_then_stays_quiet(without_core):
    with pytest.warns(CoreUnavailableWarning) as caught:
        for _ in range(2):
            datafog.scan("mail jane@example.com")
    assert len(caught) == 1


def test_explicit_python_does_not_warn():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", CoreUnavailableWarning)
        assert datafog.scan("mail jane@example.com", backend="python").entities


def test_env_override_selects_the_python_engine(monkeypatch):
    pytest.importorskip("datafog_core")
    monkeypatch.setenv(engine.BACKEND_ENV, "python")
    assert engine.resolve_backend(None, "regex") == "python"


def test_explicit_backend_beats_the_env(monkeypatch):
    pytest.importorskip("datafog_core")
    monkeypatch.setenv(engine.BACKEND_ENV, "python")
    assert engine.resolve_backend("rust", "regex") == "rust"


def test_env_is_case_and_space_insensitive(monkeypatch):
    pytest.importorskip("datafog_core")
    monkeypatch.setenv(engine.BACKEND_ENV, "  AUTO ")
    assert engine.resolve_backend(None, "regex") == "rust"


def test_unknown_env_value_rejected(monkeypatch):
    monkeypatch.setenv(engine.BACKEND_ENV, "gpu")
    with pytest.raises(ValueError, match="backend must be one of"):
        engine.scan("text", "regex")


def test_explicit_rust_without_core_still_raises(without_core):
    with pytest.raises(ImportError, match="datafog\\[rust\\]"):
        datafog.scan("mail jane@example.com", backend="rust")


def test_person_selection_without_model_raises_a_pin(monkeypatch):
    from types import SimpleNamespace

    meta = {
        "contract_version": 1,
        "supported_entities": ["EMAIL", "PERSON"],
        "default_entities": ["EMAIL"],
        "locales": {"en-US": {"enabled_entities": []}},
        "entities": {
            "EMAIL": {
                "scopes": ["structured", "text"],
                "activation": {"kind": "default"},
            },
            "PERSON": {"scopes": ["structured"], "activation": {"kind": "default"}},
        },
    }
    stub = SimpleNamespace(capabilities=lambda: meta, scan=lambda text, config=None: [])
    monkeypatch.setitem(__import__("sys").modules, "datafog_core", stub)
    monkeypatch.setattr(engine, "_cnn_cache", None)
    with pytest.raises(ValueError, match="embedded model"):
        datafog.scan("Jane Doe", entity_types=["PERSON"], backend="rust")


def test_native_findings_are_classified_as_regex_provenance():
    pytest.importorskip("datafog_core")
    result = datafog.scan("mail jane@example.com")
    assert result.engine_used == "regex"
    assert result.entities[0].engine == "regex"
    assert result.entities[0].confidence == 1.0
