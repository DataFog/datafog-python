"""Benchmark suite implementations.

Each ``suite_*`` function returns a list of Measurements. Suites verify
their expected detections against ``payloads/manifest.json`` *before*
timing anything, so the suite cannot silently benchmark an engine that
stopped detecting.

Suites raise :class:`SuiteUnavailable` when an optional dependency is
missing; the runner reports the skip and the install hint.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from _timing import Measurement, bench, bench_wall

PAYLOAD_DIR = Path(__file__).parent / "payloads"

# The comparison suites pin the *small* English model. This is deliberately
# favorable to spaCy/Presidio (smaller model = faster inference), so the
# measured speed ratios are lower bounds, not cherry-picked upper bounds.
COMPARISON_SPACY_MODEL = "en_core_web_sm"

# Presidio's names for the same four entity types the datafog suites use.
PRESIDIO_ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN"]


class SuiteUnavailable(Exception):
    """Raised when a suite's optional dependencies are not installed."""


def load_manifest() -> dict[str, Any]:
    return json.loads((PAYLOAD_DIR / "manifest.json").read_text())


def _scan_counts(text: str, entity_types: list[str]) -> dict[str, int]:
    import datafog

    counts: dict[str, int] = {}
    for entity in datafog.scan(
        text, engine="regex", entity_types=entity_types
    ).entities:
        counts[entity.type] = counts.get(entity.type, 0) + 1
    return counts


def _verify_counts(
    text: str, entity_types: list[str], expected: dict[str, int], name: str
) -> None:
    actual = _scan_counts(text, entity_types)
    if actual != expected:
        raise RuntimeError(
            f"payload {name}: detected entity counts {actual} do not match "
            f"manifest {expected} — refusing to benchmark unverified detection"
        )


def _core_payloads() -> list[tuple[str, str, dict[str, Any]]]:
    manifest = load_manifest()
    entity_types = manifest["entity_types"]
    payloads = []
    for name, spec in sorted(
        manifest["payloads"].items(), key=lambda kv: kv[1]["bytes"]
    ):
        text = (PAYLOAD_DIR / name).read_text()
        _verify_counts(text, entity_types, spec["expected_counts"], name)
        payloads.append((name, text, spec))
    return payloads


def _throughput(size_bytes: int, median_us: float) -> float:
    # bytes / microsecond is numerically identical to MB/s (1e6 / 1e6).
    return size_bytes / median_us


def suite_core(quick: bool) -> list[Measurement]:
    """datafog.scan / datafog.redact with the regex engine on pinned payloads."""
    import datafog

    entity_types = load_manifest()["entity_types"]
    repeats = 3 if quick else 5
    results = []
    for name, text, spec in _core_payloads():
        for op, func in (
            (
                "scan",
                lambda t=text: datafog.scan(
                    t, engine="regex", entity_types=entity_types
                ),
            ),
            (
                "redact",
                lambda t=text: datafog.redact(
                    t, engine="regex", entity_types=entity_types
                ),
            ),
        ):
            m = bench(
                "core",
                f"{op} {name}",
                func,
                repeats=repeats,
                meta={
                    "bytes": spec["bytes"],
                    "entities": sum(spec["expected_counts"].values()),
                },
            )
            throughput = round(_throughput(spec["bytes"], m.median), 1)
            results.append(
                dataclasses.replace(m, meta={**m.meta, "throughput_mb_s": throughput})
            )
    return results


def suite_guardrail(quick: bool) -> list[Measurement]:
    """DataFogGuardrail (LiteLLM) per-request latency, in-process."""
    try:
        from datafog.integrations.litellm_guardrail import DataFogGuardrail
    except ImportError as exc:
        raise SuiteUnavailable(
            f"litellm/fastapi not installed ({exc.name}) — "
            "pip install -r benchmarks/requirements.txt"
        ) from exc
    import datafog

    clean = json.loads((PAYLOAD_DIR / "chat_request_clean.json").read_text())
    pii = json.loads((PAYLOAD_DIR / "chat_request_pii.json").read_text())
    guardrail = DataFogGuardrail(action="redact")
    loop = asyncio.new_event_loop()
    try:
        # Verify behavior before timing: PII request must come back redacted,
        # clean request must pass through untouched.
        redacted = loop.run_until_complete(
            guardrail.async_pre_call_hook(None, None, pii, "completion")
        )
        if "[EMAIL_" not in redacted["messages"][1]["content"]:
            raise RuntimeError("guardrail did not redact the PII chat request")
        passthrough = loop.run_until_complete(
            guardrail.async_pre_call_hook(None, None, clean, "completion")
        )
        if passthrough is not clean:
            raise RuntimeError("guardrail modified a clean chat request")

        repeats = 3 if quick else 5

        async def _noop() -> None:
            pass

        def timed(data: dict) -> Callable[[], Any]:
            return lambda: loop.run_until_complete(
                guardrail.async_pre_call_hook(None, None, data, "completion")
            )

        pii_msg = pii["messages"][1]["content"]
        entity_types = guardrail.entity_types
        results = [
            bench(
                "guardrail",
                "event-loop dispatch (harness overhead)",
                lambda: loop.run_until_complete(_noop()),
                repeats=repeats,
                meta={
                    "note": "subtract from per-request figures; a live proxy's loop is already running"
                },
            ),
            bench(
                "guardrail",
                "pre_call, clean 2-message request",
                timed(clean),
                repeats=repeats,
                meta={
                    "note": "the common case: scan finds nothing, request passes through"
                },
            ),
            bench(
                "guardrail",
                "pre_call, PII 2-message request (redact)",
                timed(pii),
                repeats=repeats,
                meta={
                    "note": "includes litellm's guardrail-intervention logging record"
                },
            ),
            bench(
                "guardrail",
                "single message redact (datafog.redact)",
                lambda: datafog.redact(
                    pii_msg, engine="regex", entity_types=entity_types
                ),
                repeats=repeats,
                meta={"bytes": len(pii_msg.encode())},
            ),
        ]
    finally:
        loop.close()
    return results


def _hook_command() -> list[str]:
    exe = shutil.which("datafog-hook")
    if exe:
        return [exe]
    return [sys.executable, "-m", "datafog.integrations.claude_code"]


def suite_hook(quick: bool) -> list[Measurement]:
    """datafog-hook end-to-end (fresh process per call, as Claude Code runs it)."""
    payload = (PAYLOAD_DIR / "hook_pretooluse.json").read_text()
    cmd = _hook_command()

    def run_once() -> subprocess.CompletedProcess:
        return subprocess.run(cmd, input=payload, capture_output=True, text=True)

    # Verify before timing: the hook must actually fire on this payload.
    proc = run_once()
    if (
        proc.returncode != 0
        or "PreToolUse" not in proc.stdout
        or "EMAIL" not in proc.stdout
    ):
        raise RuntimeError(
            f"datafog-hook did not flag the pinned payload "
            f"(exit {proc.returncode}, stdout {proc.stdout!r}, stderr {proc.stderr!r})"
        )

    from datafog.integrations.claude_code import run as hook_run

    payload_obj = json.loads(payload)
    return [
        bench_wall(
            "hook",
            "datafog-hook end-to-end (subprocess, incl. Python startup)",
            run_once,
            iterations=10 if quick else 30,
            meta={"command": " ".join(cmd)},
        ),
        bench(
            "hook",
            "hook scan only (in-process run())",
            lambda: hook_run(payload_obj, {}),
            repeats=3 if quick else 5,
            meta={
                "note": "the scan itself; the rest of the end-to-end figure is process startup"
            },
        ),
    ]


def suite_spacy(quick: bool) -> list[Measurement]:
    """datafog regex engine vs the spaCy NER pipeline on the same payloads."""
    try:
        from datafog.processing.text_processing.spacy_pii_annotator import (
            SpacyPIIAnnotator,
        )

        annotator = SpacyPIIAnnotator.create(model_name=COMPARISON_SPACY_MODEL)
    except Exception as exc:
        raise SuiteUnavailable(
            f"spaCy model unavailable ({exc}) — pip install -r benchmarks/requirements.txt "
            f"&& python -m spacy download {COMPARISON_SPACY_MODEL}"
        ) from exc
    import datafog

    entity_types = load_manifest()["entity_types"]
    results = []
    for name, text, spec in _core_payloads():
        if quick and spec["bytes"] > 20_000:
            continue
        regex_m = bench(
            "spacy",
            f"regex scan {name}",
            lambda t=text: datafog.scan(t, engine="regex", entity_types=entity_types),
            repeats=3,
            meta={"bytes": spec["bytes"]},
        )
        spacy_m = bench(
            "spacy",
            f"spaCy NER ({COMPARISON_SPACY_MODEL}) {name}",
            lambda t=text: annotator.annotate(t),
            repeats=3,
            meta={
                "bytes": spec["bytes"],
                "note": "model load excluded; different entity classes than regex",
            },
        )
        speedup = round(spacy_m.median / regex_m.median, 1)
        spacy_m = dataclasses.replace(
            spacy_m, meta={**spacy_m.meta, "regex_speedup_x": speedup}
        )
        results.extend([regex_m, spacy_m])
    return results


def suite_presidio(quick: bool) -> list[Measurement]:
    """presidio-analyzer on the same payloads, same four entity types."""
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError as exc:
        raise SuiteUnavailable(
            f"presidio-analyzer not installed ({exc.name}) — "
            "pip install -r benchmarks/requirements.txt"
        ) from exc
    import datafog

    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": COMPARISON_SPACY_MODEL}],
    }
    start = time.perf_counter()
    engine = AnalyzerEngine(
        nlp_engine=NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
    )
    setup_ms = (time.perf_counter() - start) * 1e3

    entity_types = load_manifest()["entity_types"]
    results = [
        Measurement(
            suite="presidio",
            name=f"AnalyzerEngine setup ({COMPARISON_SPACY_MODEL})",
            unit="ms/run",
            median=setup_ms,
            mean=setup_ms,
            stdev=0.0,
            best=setup_ms,
            inner_loops=1,
            repeats=1,
            meta={"note": "one-time cost, excluded from per-scan figures below"},
        )
    ]
    for name, text, spec in _core_payloads():
        if quick and spec["bytes"] > 20_000:
            continue
        datafog_m = bench(
            "presidio",
            f"datafog regex scan {name}",
            lambda t=text: datafog.scan(t, engine="regex", entity_types=entity_types),
            repeats=3,
            meta={"bytes": spec["bytes"], "detected": _scan_counts(text, entity_types)},
        )
        presidio_counts: dict[str, int] = {}
        for r in engine.analyze(text=text, entities=PRESIDIO_ENTITIES, language="en"):
            presidio_counts[r.entity_type] = presidio_counts.get(r.entity_type, 0) + 1
        presidio_m = bench(
            "presidio",
            f"presidio analyze {name}",
            lambda t=text: engine.analyze(
                text=t, entities=PRESIDIO_ENTITIES, language="en"
            ),
            repeats=3,
            meta={
                "bytes": spec["bytes"],
                "detected": dict(sorted(presidio_counts.items())),
            },
        )
        speedup = round(presidio_m.median / datafog_m.median, 1)
        presidio_m = dataclasses.replace(
            presidio_m, meta={**presidio_m.meta, "datafog_speedup_x": speedup}
        )
        results.extend([datafog_m, presidio_m])
    return results


SUITES: dict[str, Callable[[bool], list[Measurement]]] = {
    "core": suite_core,
    "guardrail": suite_guardrail,
    "hook": suite_hook,
    "spacy": suite_spacy,
    "presidio": suite_presidio,
}
