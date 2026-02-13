"""Corpus-driven detection accuracy tests."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pytest

from datafog.engine import scan
from datafog.exceptions import EngineNotAvailable

CORPUS_DIR = Path("tests/corpus")

STRUCTURED_TYPES = {
    "EMAIL",
    "PHONE",
    "SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "DATE",
    "ZIP_CODE",
}

TYPE_ALIASES = {
    "DOB": "DATE",
    "ZIP": "ZIP_CODE",
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "ADDRESS",
    "PHONE_NUMBER": "PHONE",
    "SOCIAL_SECURITY_NUMBER": "SSN",
    "CREDIT_CARD_NUMBER": "CREDIT_CARD",
    "DATE_OF_BIRTH": "DATE",
}

ALL_ENGINES = ["regex", "spacy", "gliner", "smart"]
NER_ENGINES = ["spacy", "gliner", "smart"]
FAST_ENGINES = ["regex", "smart"]
SLOW_ENGINES = ["spacy", "gliner"]

KNOWN_LIMITATION_XFAILS: dict[tuple[str, str, str], str] = {
    (
        "smart",
        "negative",
        "hex-not-ip",
    ): "GLiNER occasionally over-labels hexadecimal identifiers as IP-like entities.",
    (
        "smart",
        "unstructured",
        "person-first-name-ambiguous",
    ): "Ambiguous single-token names are model-dependent and may be typed as ORG instead of PERSON.",
    (
        "smart",
        "unstructured",
        "person-non-western",
    ): "Current smart stack has unstable recall for this non-Latin corpus variant.",
    (
        "smart",
        "unstructured",
        "person-arabic",
    ): "Current smart stack has unstable recall for this Arabic corpus variant.",
    (
        "smart",
        "edge",
        "unicode-chinese-name",
    ): "Non-Latin PERSON detection in this edge case is a known limitation of current models.",
    (
        "smart",
        "mixed",
        "cross-border",
    ): "Model may merge address/location spans into a single ADDRESS entity in cross-border examples.",
    (
        "spacy",
        "negative",
        "isbn-not-ssn",
    ): "spaCy may label uppercase acronyms like ISBN as organizations in negative controls.",
    (
        "spacy",
        "negative",
        "hex-not-ip",
    ): "spaCy may label short uppercase tokens (for example IP) from context as organizations.",
    (
        "spacy",
        "negative",
        "order-id-not-zip",
    ): "spaCy may classify temporal words (for example tomorrow) as DATE in negative controls.",
    (
        "spacy",
        "negative",
        "time-not-phone",
    ): "spaCy may classify UTC as organization-like token in negative controls.",
    (
        "spacy",
        "negative",
        "date-like-invalid",
    ): "spaCy may treat malformed date-like strings as DATE entities.",
    (
        "gliner",
        "negative",
        "hex-not-ip",
    ): "GLiNER occasionally over-labels hexadecimal identifiers as IP-like entities.",
    (
        "gliner",
        "unstructured",
        "person-first-name-ambiguous",
    ): "Ambiguous single-token names are model-dependent and may be typed as ORG instead of PERSON.",
    (
        "gliner",
        "unstructured",
        "person-non-western",
    ): "Current GLiNER model has unstable recall for this non-Latin corpus variant.",
    (
        "gliner",
        "unstructured",
        "person-arabic",
    ): "Current GLiNER model has unstable recall for this Arabic corpus variant.",
    (
        "spacy",
        "unstructured",
        "person-first-name-ambiguous",
    ): "Ambiguous single-token names are model-dependent and may be typed as ORG instead of PERSON.",
    (
        "spacy",
        "unstructured",
        "person-non-western",
    ): "Current spaCy model has unstable recall for this non-Latin corpus variant.",
    (
        "spacy",
        "unstructured",
        "person-common-word-name",
    ): "Common-word names can be typed as organizations by the default spaCy model.",
    (
        "spacy",
        "unstructured",
        "person-arabic",
    ): "Current spaCy model has unstable recall for this Arabic corpus variant.",
    (
        "spacy",
        "unstructured",
        "address-us",
    ): "Default spaCy model does not reliably emit full ADDRESS spans for this US-address format.",
    (
        "spacy",
        "mixed",
        "json-payload",
    ): "spaCy can miss PERSON inside compact JSON-like payload strings while regex still catches structured PII.",
    (
        "spacy",
        "mixed",
        "ops-json",
    ): "spaCy can miss PERSON entities in terse operational JSON snippets.",
    (
        "spacy",
        "mixed",
        "cross-border",
    ): "spaCy may miss address/location decomposition in cross-border address strings.",
    (
        "gliner",
        "mixed",
        "cross-border",
    ): "GLiNER may merge address/location spans into a single ADDRESS entity in cross-border examples.",
    (
        "spacy",
        "edge",
        "unicode-chinese-name",
    ): "Default spaCy model does not reliably identify PERSON entities in this non-Latin edge case.",
    (
        "spacy",
        "edge",
        "json-nested",
    ): "spaCy may mis-segment nested JSON-like strings and miss the expected PERSON span.",
    (
        "gliner",
        "edge",
        "unicode-chinese-name",
    ): "Current GLiNER model does not reliably identify PERSON entities in this non-Latin edge case.",
}


def load_corpus(filename: str) -> list[dict[str, Any]]:
    return json.loads((CORPUS_DIR / filename).read_text(encoding="utf-8"))


def _canon_type(entity_type: str) -> str:
    raw = entity_type.upper().strip()
    return TYPE_ALIASES.get(raw, raw)


def _extract_entities(text: str, engine: str) -> list[dict[str, Any]]:
    try:
        result = scan(text=text, engine=engine)
    except (ImportError, EngineNotAvailable) as exc:
        pytest.skip(f"{engine} engine unavailable in this environment: {exc}")

    entities: list[dict[str, Any]] = []
    for entity in result.entities:
        if not entity.text or not entity.text.strip():
            continue
        entities.append(
            {
                "type": _canon_type(entity.type),
                "text": entity.text,
                "start": entity.start,
                "end": entity.end,
                "engine": entity.engine,
            }
        )

    return entities


def _required_expected(
    expected: Iterable[dict[str, Any]], engine: str, corpus_kind: str
) -> list[dict[str, Any]]:
    expected_list = list(expected)
    if corpus_kind == "unstructured" and engine == "regex":
        return []
    if engine == "regex" and corpus_kind in {"mixed", "edge"}:
        return [e for e in expected_list if _canon_type(e["type"]) in STRUCTURED_TYPES]
    return expected_list


def _xfail_if_known_limitation(case: dict[str, Any], engine: str, corpus_kind: str) -> None:
    key = (engine, corpus_kind, case["id"])
    reason = KNOWN_LIMITATION_XFAILS.get(key)
    if reason:
        pytest.xfail(reason)


def _assert_expected_found(
    case: dict[str, Any], engine: str, corpus_kind: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = case["input"]
    actual = _extract_entities(text, engine)
    expected = _required_expected(case["expected_entities"], engine, corpus_kind)

    for exp in expected:
        exp_type = _canon_type(exp["type"])
        exp_text = exp["text"]
        matches = [
            ent
            for ent in actual
            if ent["type"] == exp_type and ent["text"] == exp_text
        ]
        if not matches:
            matches = [
                ent
                for ent in actual
                if ent["type"] == exp_type
                and (exp_text in ent["text"] or ent["text"] in exp_text)
            ]
        assert matches, (
            f"{case['id']} ({engine}) missing expected entity "
            f"{exp_type}:{exp_text!r}. Actual={actual}"
        )
        if "start" in exp and "end" in exp:
            # If offsets are available from the engine output, validate exact position.
            with_offsets = [m for m in matches if m["start"] >= 0 and m["end"] >= 0]
            if with_offsets:
                if engine == "regex" or exp_type in STRUCTURED_TYPES:
                    assert any(
                        m["start"] == exp["start"] and m["end"] == exp["end"]
                        for m in with_offsets
                    ), (
                        f"{case['id']} ({engine}) incorrect offsets for {exp_text!r}. "
                        f"Expected ({exp['start']}, {exp['end']}), got {with_offsets}"
                    )
                else:
                    # NER offsets vary by model; require overlapping spans instead of exact offsets.
                    assert any(
                        not (m["end"] <= exp["start"] or m["start"] >= exp["end"])
                        for m in with_offsets
                    ), (
                        f"{case['id']} ({engine}) non-overlapping offsets for {exp_text!r}. "
                        f"Expected overlap with ({exp['start']}, {exp['end']}), got {with_offsets}"
                    )
    return actual, expected


def _compute_metrics(
    engines: list[str], corpora: list[tuple[str, list[dict[str, Any]]]]
) -> dict[str, Any]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    by_type: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    )
    failures: list[dict[str, Any]] = []

    for engine in engines:
        for corpus_kind, cases in corpora:
            for case in cases:
                actual = _extract_entities(case["input"], engine)
                expected = _required_expected(case["expected_entities"], engine, corpus_kind)
                expected_set = {(_canon_type(e["type"]), e["text"]) for e in expected}
                actual_set = {(e["type"], e["text"]) for e in actual}

                tp = expected_set & actual_set
                fp = actual_set - expected_set
                fn = expected_set - actual_set

                totals[engine]["tp"] += len(tp)
                totals[engine]["fp"] += len(fp)
                totals[engine]["fn"] += len(fn)

                for etype, _ in tp:
                    by_type[engine][etype]["tp"] += 1
                for etype, _ in fp:
                    by_type[engine][etype]["fp"] += 1
                for etype, _ in fn:
                    by_type[engine][etype]["fn"] += 1

                if fp or fn:
                    failures.append(
                        {
                            "engine": engine,
                            "corpus": corpus_kind,
                            "case_id": case["id"],
                            "false_positives": sorted(fp),
                            "false_negatives": sorted(fn),
                        }
                    )

    def _prf(scores: dict[str, int]) -> dict[str, float]:
        tp = scores["tp"]
        fp = scores["fp"]
        fn = scores["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    result: dict[str, Any] = {"overall": {}, "by_entity_type": {}, "failures": failures}
    for engine, scores in totals.items():
        result["overall"][engine] = _prf(scores)
        result["by_entity_type"][engine] = {
            entity_type: _prf(s) for entity_type, s in sorted(by_type[engine].items())
        }
    return result


@pytest.mark.parametrize("case", load_corpus("structured_pii.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", FAST_ENGINES)
def test_structured_pii_detection_fast(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "structured")
    _assert_expected_found(case, engine, "structured")


@pytest.mark.slow
@pytest.mark.parametrize("case", load_corpus("structured_pii.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", SLOW_ENGINES)
def test_structured_pii_detection_slow(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "structured")
    _assert_expected_found(case, engine, "structured")


@pytest.mark.parametrize(
    "case", load_corpus("negative_cases.json"), ids=lambda c: c["id"]
)
@pytest.mark.parametrize("engine", FAST_ENGINES)
def test_negative_cases_fast(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "negative")
    actual = _extract_entities(case["input"], engine)
    assert not actual, f"{case['id']} ({engine}) false positives: {actual}"


@pytest.mark.slow
@pytest.mark.parametrize(
    "case", load_corpus("negative_cases.json"), ids=lambda c: c["id"]
)
@pytest.mark.parametrize("engine", SLOW_ENGINES)
def test_negative_cases_slow(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "negative")
    actual = _extract_entities(case["input"], engine)
    assert not actual, f"{case['id']} ({engine}) false positives: {actual}"


@pytest.mark.parametrize(
    "case", load_corpus("unstructured_pii.json"), ids=lambda c: c["id"]
)
@pytest.mark.parametrize("engine", ["smart"])
def test_unstructured_pii_detection_fast(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "unstructured")
    _assert_expected_found(case, engine, "unstructured")


@pytest.mark.slow
@pytest.mark.parametrize(
    "case", load_corpus("unstructured_pii.json"), ids=lambda c: c["id"]
)
@pytest.mark.parametrize("engine", ["gliner", "spacy"])
def test_unstructured_pii_detection_slow(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "unstructured")
    _assert_expected_found(case, engine, "unstructured")


@pytest.mark.parametrize("case", load_corpus("mixed_pii.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", FAST_ENGINES)
def test_mixed_pii_detection_fast(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "mixed")
    _assert_expected_found(case, engine, "mixed")


@pytest.mark.slow
@pytest.mark.parametrize("case", load_corpus("mixed_pii.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", SLOW_ENGINES)
def test_mixed_pii_detection_slow(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "mixed")
    _assert_expected_found(case, engine, "mixed")


@pytest.mark.parametrize("case", load_corpus("edge_cases.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", FAST_ENGINES)
def test_edge_case_detection_fast(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "edge")
    _assert_expected_found(case, engine, "edge")


@pytest.mark.slow
@pytest.mark.parametrize("case", load_corpus("edge_cases.json"), ids=lambda c: c["id"])
@pytest.mark.parametrize("engine", SLOW_ENGINES)
def test_edge_case_detection_slow(case: dict[str, Any], engine: str) -> None:
    _xfail_if_known_limitation(case, engine, "edge")
    _assert_expected_found(case, engine, "edge")


@pytest.mark.slow
def test_accuracy_metrics_snapshot() -> None:
    corpora = [
        ("structured", load_corpus("structured_pii.json")),
        ("unstructured", load_corpus("unstructured_pii.json")),
        ("mixed", load_corpus("mixed_pii.json")),
        ("negative", load_corpus("negative_cases.json")),
        ("edge", load_corpus("edge_cases.json")),
    ]
    metrics = _compute_metrics(ALL_ENGINES, corpora)
    output_path = Path("docs/audit/02-detection-accuracy-metrics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    assert "overall" in metrics and metrics["overall"]
