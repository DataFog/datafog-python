import os
import subprocess
import sys
from pathlib import Path

import datafog
from datafog.engine import scan_and_redact


def _run_isolated_python(script: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path.cwd())
    env.pop("DATAFOG_TELEMETRY", None)
    env["DATAFOG_NO_TELEMETRY"] = "1"
    env["DO_NOT_TRACK"] = "1"
    return subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )


def test_import_scan_and_redact_do_not_open_network() -> None:
    _run_isolated_python(
        """
import socket
import urllib.request

def blocked(*_args, **_kwargs):
    raise AssertionError("network access is blocked in this test")

socket.create_connection = blocked
urllib.request.urlopen = blocked

import datafog

scan_result = datafog.scan("Email jane@example.com or call 415-555-1212")
assert {entity.type for entity in scan_result.entities} >= {"EMAIL", "PHONE"}

redact_result = datafog.redact("Email jane@example.com or call 415-555-1212")
assert "jane@example.com" not in redact_result.redacted_text
assert "415-555-1212" not in redact_result.redacted_text
"""
    )


def test_redact_positional_strategy_remains_compatible() -> None:
    public_result = datafog.redact(
        "Email jane@example.com",
        None,
        "regex",
        None,
        "mask",
    )
    engine_result = scan_and_redact(
        "Email jane@example.com",
        "regex",
        None,
        "mask",
    )

    assert public_result.redacted_text == engine_result.redacted_text
    assert public_result.redacted_text != "Email jane@example.com"


def test_core_defaults_do_not_initialize_optional_engines(monkeypatch) -> None:
    import datafog
    import datafog.engine as engine

    def fail_optional_engine_probe():
        raise AssertionError("core defaults should not initialize optional engines")

    monkeypatch.setattr(engine, "_get_spacy_annotator", fail_optional_engine_probe)
    monkeypatch.setattr(engine, "_get_gliner_annotator", fail_optional_engine_probe)

    scan_result = datafog.scan("Email jane@example.com")
    assert [entity.type for entity in scan_result.entities] == ["EMAIL"]

    redact_result = datafog.redact("Email jane@example.com")
    assert redact_result.redacted_text == "Email [EMAIL_1]"

    guardrail = datafog.protect()
    guarded = guardrail.filter("Email jane@example.com")
    assert guarded.redacted_text == "Email [EMAIL_1]"


def test_import_probes_do_not_load_optional_models() -> None:
    _run_isolated_python(
        """
import sys
import types

def blocked_model_load(*_args, **_kwargs):
    raise AssertionError("import should not load optional models")

spacy = types.ModuleType("spacy")
spacy.load = blocked_model_load
spacy.cli = types.SimpleNamespace(download=blocked_model_load)
spacy.util = types.SimpleNamespace(get_installed_models=lambda: [])
sys.modules["spacy"] = spacy

gliner = types.ModuleType("gliner")

class GLiNER:
    @staticmethod
    def from_pretrained(*_args, **_kwargs):
        blocked_model_load()

gliner.GLiNER = GLiNER
sys.modules["gliner"] = gliner

import datafog

assert datafog.scan("Email jane@example.com").entities
"""
    )
