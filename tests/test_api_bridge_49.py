"""Compatibility facade and native-schema preview release gates."""

import importlib.util
import inspect
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import datafog
from datafog import engine, v5
from datafog.compat import v4


@pytest.mark.parametrize("name", ["Entity", "ScanResult", "RedactResult"])
def test_legacy_types_retain_identity(name):
    assert getattr(datafog, name) is getattr(v4, name) is getattr(engine, name)


def test_existing_positional_calls_match_compatibility_facade():
    text = "Email jane@example.com"
    args = (text, "regex", ["EMAIL"], None, None, None)
    assert datafog.scan(*args) == v4.scan(*args)
    args = (text, None, "regex", ["EMAIL"], "token", "llm", None, None, None)
    assert datafog.redact(*args) == v4.redact(*args)
    assert datafog.redact(*args).redacted_text == "Email [EMAIL_1]"


@pytest.mark.parametrize("function", [datafog.scan, datafog.redact, v4.scan, v4.redact])
def test_backend_is_additive_keyword_only(function):
    parameter = inspect.signature(function).parameters["backend"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default == "python"


@pytest.mark.parametrize("name", ["scan", "redact"])
def test_top_level_delegates_backend_to_facade(name):
    with patch.object(v4, name, return_value="sentinel") as delegate:
        assert getattr(datafog, name)("text", backend="rust") == "sentinel"
    assert delegate.call_args.kwargs["backend"] == "rust"


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_explicit_entities_do_not_scan(backend):
    with patch.object(v4, "_scan_and_redact", side_effect=AssertionError("scanned")):
        assert (
            datafog.redact("text", entities=[], backend=backend).redacted_text == "text"
        )


def test_explicit_entities_validate_backend():
    with pytest.raises(ValueError, match="backend"):
        datafog.redact("text", entities=[], backend="unknown")


def test_import_and_explicit_redaction_without_native_dependency():
    code = """
import sys
class BlockNative:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "datafog_core" or fullname.startswith("datafog_core."):
            raise AssertionError("native import attempted")
sys.meta_path.insert(0, BlockNative())
import datafog
import datafog.v5
from datafog.compat import v4
assert datafog.redact("text", entities=[], backend="rust").redacted_text == "text"
assert "datafog_core" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_missing_preview_dependency_has_actionable_error():
    with patch.object(v5, "import_module", side_effect=ImportError("missing")):
        with pytest.raises(ImportError, match=r"datafog\[rust\]"):
            v5.__getattr__("scan")


@pytest.mark.parametrize("namespace", [v4, v5])
@pytest.mark.parametrize("name", ["detect", "process"])
def test_new_namespaces_do_not_export_deprecated_shims(namespace, name):
    assert name not in namespace.__all__
    assert not hasattr(namespace, name)


@pytest.mark.parametrize("name", ["detect", "process"])
def test_shims_explicitly_revise_removal_promise(name):
    with pytest.warns(FutureWarning, match="removed in 5.0") as captured:
        getattr(datafog, name)("plain text")
    assert "earlier promise" in str(captured[0].message)
    assert "has been revised" in str(captured[0].message)


def test_real_native_exports_and_transformation():
    core = pytest.importorskip("datafog_core")
    for name in v5.__all__:
        assert getattr(v5, name) is getattr(core, name)
    findings = v5.scan("Email jane@example.com")
    assert isinstance(findings[0], v5.Finding)
    result = v5.scan_and_transform(
        "Email jane@example.com", {"transform": {"default": {"strategy": "redact"}}}
    )
    assert isinstance(result, v5.TransformResult)
    assert result.text == "Email [EMAIL]"


def test_preview_discovery_is_lazy_and_exports_are_cached(monkeypatch):
    # A separate module object avoids cached exports from native integration tests.
    spec = importlib.util.spec_from_file_location("isolated_preview", v5.__file__)
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    core = SimpleNamespace(**{name: object() for name in preview.__all__})
    loader = Mock(return_value=core)
    monkeypatch.setattr(preview, "import_module", loader)

    assert set(preview.__all__) <= set(dir(preview))
    with pytest.raises(AttributeError, match="unrecognized"):
        preview.unrecognized
    loader.assert_not_called()

    for name in preview.__all__:
        assert getattr(preview, name) is getattr(core, name)
    assert loader.call_count == len(preview.__all__)
    loader.reset_mock()
    for name in preview.__all__:
        assert getattr(preview, name) is getattr(core, name)
    loader.assert_not_called()


@pytest.mark.parametrize("redact", [datafog.redact, v4.redact])
def test_compatibility_facade_rejects_unknown_preset(redact):
    with pytest.raises(ValueError, match="preset must be one of"):
        redact("plain text", preset="unknown")


@pytest.mark.parametrize("option", ["allowlist", "allowlist_patterns"])
def test_compatibility_facade_rejects_allowlists_with_explicit_entities(option):
    with pytest.raises(ValueError, match="cannot be combined with explicit entities"):
        v4.redact("plain text", entities=[], **{option: ["plain text"]})
