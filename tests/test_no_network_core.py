import os
import subprocess
import sys
from pathlib import Path


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

batch_result = datafog.redact_many(["Email jane@example.com", "Call 415-555-1212"])
assert batch_result.redacted_texts == ["Email [EMAIL_1]", "Call [PHONE_1]"]
"""
    )


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

    batch_result = datafog.redact_many(
        ["Email jane@example.com", "Email support@example.com"]
    )
    assert batch_result.redacted_texts == ["Email [EMAIL_1]", "Email [EMAIL_2]"]

    guardrail = datafog.protect()
    guarded = guardrail.filter("Email jane@example.com")
    assert guarded.redacted_text == "Email [EMAIL_1]"

    sanitized = datafog.sanitize("Email jane@example.com")
    assert sanitized == "Email [EMAIL_1]"

    prompt_result = datafog.scan_prompt("Email jane@example.com")
    assert [entity.type for entity in prompt_result.entities] == ["EMAIL"]

    output_result = datafog.filter_output("Email jane@example.com")
    assert output_result.redacted_text == "Email [EMAIL_1]"

    agent_guardrail = datafog.create_guardrail()
    agent_guarded = agent_guardrail.filter("Email jane@example.com")
    assert agent_guarded.redacted_text == "Email [EMAIL_1]"


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


def test_core_path_does_not_import_optional_dependency_modules() -> None:
    _run_isolated_python(
        """
import importlib.abc
import sys

blocked = {
    "aiohttp",
    "certifi",
    "gliner",
    "PIL",
    "pyspark",
    "pytesseract",
    "spacy",
    "torch",
    "transformers",
}

class BlockOptionalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise AssertionError(f"optional dependency imported: {fullname}")
        return None

sys.meta_path.insert(0, BlockOptionalImports())

import datafog

assert datafog.scan("Email jane@example.com").entities
assert datafog.redact("Email jane@example.com").redacted_text == "Email [EMAIL_1]"
assert datafog.redact_many(["Email jane@example.com"]).redacted_texts == ["Email [EMAIL_1]"]
assert datafog.protect().filter("Email jane@example.com").redacted_text == "Email [EMAIL_1]"
assert datafog.sanitize("Email jane@example.com") == "Email [EMAIL_1]"
assert datafog.scan_prompt("Email jane@example.com").entities
assert datafog.filter_output("Email jane@example.com").redacted_text == "Email [EMAIL_1]"
assert datafog.create_guardrail().filter("Email jane@example.com").redacted_text == "Email [EMAIL_1]"
"""
    )
