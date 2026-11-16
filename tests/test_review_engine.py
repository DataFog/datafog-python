"""Regression contracts for the 4.11 review's engine and annotation findings."""

import hashlib
import hmac
import random
from types import SimpleNamespace

import pytest

from datafog import engine
from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator
from datafog.processing.text_processing.regex_annotator.regex_annotator import (
    RegexAnnotator,
)
from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from datafog.services.text_service import TextService


def test_native_surrogate_normalization_preserves_source_and_offsets():
    text = "\ud800😀 ssn 123-45-6789 \udfff"
    result = engine.scan(text, engine="regex", backend="rust")
    assert result.text == text
    assert any(entity.type == "SSN" for entity in result.entities)
    assert all(text[item.start : item.end] == item.text for item in result.entities)
    assert "123-45-6789" not in engine.redact(text, result.entities).redacted_text


def test_interval_selection_preserves_longest_and_tiebreak_contract():
    rng = random.Random(113)
    for _ in range(30):
        entities = [
            engine.Entity(
                rng.choice(["PHONE", "SSN"]),
                "",
                start,
                start + rng.randint(1, 30),
                rng.random(),
                "regex",
            )
            for start in [rng.randint(0, 200) for _ in range(100)]
        ]
        expected = []
        for entity in sorted(
            entities,
            key=lambda item: (
                -engine._entity_length(item),
                -engine.ENTITY_TYPE_PRIORITY.get(item.type, 0),
                -item.confidence,
                item.start,
                item.end,
                item.type,
            ),
        ):
            if not any(engine._entities_overlap(entity, kept) for kept in expected):
                expected.append(entity)
        assert engine._suppress_overlapping_entities(entities) == sorted(
            expected, key=lambda item: (item.start, item.end, item.type)
        )


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("value", ["john.doe@example.com", "123-45-6789"])
def test_text_service_retains_findings_at_chunk_boundaries(value, structured):
    text = "x" * 996 + " " + value + " tail"
    result = TextService(text_chunk_length=1000).annotate_text_sync(text, structured)
    if structured:
        assert any(
            item.text == value and text[item.start : item.end] == value
            for item in result
        )
    else:
        assert any(value in items for items in result.values())


def test_spacy_uses_original_offsets_and_does_not_turn_relative_dates_into_pii(
    monkeypatch,
):
    text = "Annual report prepared by Ann yesterday."
    spans = [
        SimpleNamespace(label_="PERSON", text="Ann", start_char=26, end_char=29),
        SimpleNamespace(label_="DATE", text="yesterday", start_char=30, end_char=39),
    ]
    annotator = SpacyPIIAnnotator(nlp=lambda _: SimpleNamespace(ents=spans))
    monkeypatch.setattr(engine, "_get_spacy_annotator", lambda: annotator)
    result = engine.scan_and_redact(text, engine="spacy")
    assert result.redacted_text == "Annual report prepared by [PERSON_1] yesterday."


def test_legacy_string_annotator_does_not_match_names_inside_words():
    result = engine._entities_from_dict(
        "Annual report by Ann.", {"PERSON": ["Ann"]}, "spacy", 0.7
    )
    assert [(item.start, item.end) for item in result] == [(17, 20)]


@pytest.mark.parametrize("mode", ["smart", "spacy", "gliner"])
def test_every_engine_keeps_native_structured_detection(monkeypatch, mode):
    monkeypatch.setattr(engine, "_gliner_entities", lambda _: [])
    monkeypatch.setattr(engine, "_spacy_entities", lambda _: [])
    text = "card 6011111111111117 ip 2001:db8::1"
    result = engine.scan_and_redact(text, engine=mode, backend="rust")
    assert {item.type for item in result.entities} == {"CREDIT_CARD", "IP_ADDRESS"}
    assert "6011111111111117" not in result.redacted_text
    assert "2001:db8::1" not in result.redacted_text


@pytest.mark.parametrize("labels", ["EMAIL", ["BOGUS"], [1], [""]])
def test_entity_type_mistakes_fail_explicitly(labels):
    with pytest.raises(ValueError, match="entity_types"):
        engine.scan("john@example.com", entity_types=labels)


@pytest.mark.parametrize("label", ["JWT", "PERSON", "ORGANIZATION", "UUID"])
def test_unavailable_fallback_labels_raise(label):
    with pytest.raises(ValueError, match="Unsupported entity_types"):
        engine.scan(
            "john@example.com", engine="regex", backend="python", entity_types=[label]
        )


@pytest.mark.parametrize("pattern", [r"(a|a)+$", r"((a+))+$"])
def test_pathological_allowlist_cannot_suppress_a_finding(pattern):
    value = "a" * 300 + "@b.com"
    entity = engine.Entity("EMAIL", value, 0, len(value), 1.0, "regex")
    assert engine._apply_allowlist([entity], None, [pattern]) == [entity]


@pytest.mark.parametrize(
    "pattern,value",
    [(r"(\d{3}){2}", "123123"), (r"(?:\d{3}-){2}\d{4}", "415-555-2671")],
)
def test_safe_quantified_allowlist_patterns_are_supported(pattern, value):
    entity = engine.Entity("PHONE", value, 0, len(value), 1.0, "regex")
    assert engine._apply_allowlist([entity], None, [pattern]) == []


@pytest.mark.parametrize(
    "annotator",
    [
        SpacyPIIAnnotator(
            nlp=lambda _: (_ for _ in ()).throw(RuntimeError("raw secret"))
        ),
        GLiNERAnnotator(
            model=SimpleNamespace(
                predict_entities=lambda *_: (_ for _ in ()).throw(
                    RuntimeError("raw secret")
                )
            ),
            entity_types=["person"],
            model_name="test",
        ),
    ],
)
def test_ner_failures_and_oversize_inputs_are_explicit(annotator):
    with pytest.raises(RuntimeError, match="annotation failed"):
        annotator.annotate("secret")
    with pytest.raises(ValueError, match="exceeds"):
        annotator.annotate("x" * 1_000_001)


@pytest.mark.parametrize(
    "label", ["passport number", "medical record number", "license number", "url"]
)
def test_gliner_extra_labels_and_original_offsets_are_preserved(monkeypatch, label):
    text = "prefix SECRET suffix"
    annotator = GLiNERAnnotator(
        model=SimpleNamespace(
            predict_entities=lambda *_: [
                {"label": label, "text": "SECRET", "start": 7, "end": 13}
            ]
        ),
        entity_types=[label],
        model_name="test",
    )
    monkeypatch.setattr(engine, "_get_gliner_annotator", lambda: annotator)
    result = engine.scan(
        text, engine="gliner", entity_types=[label.upper().replace(" ", "_")]
    )
    assert len(result.entities) == 1
    assert result.entities[0].text == "SECRET"
    assert result.entities[0].start == 7


def test_model_chunks_are_bounded_and_keep_document_offsets():
    text = "😀" * 9000 + " Jane Doe"
    calls = []

    def scan_model(chunk):
        calls.append(chunk)
        start = chunk.find("Jane Doe")
        findings = (
            []
            if start < 0
            else [
                SimpleNamespace(
                    entity_type="PERSON",
                    codepoint_range=SimpleNamespace(start=start, end=start + 8),
                    matched_text="Jane Doe",
                )
            ]
        )
        return SimpleNamespace(findings=findings)

    findings = engine._cnn_findings(
        SimpleNamespace(scan_model=scan_model), {"PERSON"}, text
    )
    assert len(calls) >= 3 and max(len(chunk.encode()) for chunk in calls) <= 16384
    assert any(
        offset + item.codepoint_range.start == text.index("Jane Doe")
        for offset, item in findings
    )


def test_token_collision_and_repeated_value_mapping():
    text = "[EMAIL_1] a@b.com and a@b.com"
    result = engine.scan_and_redact(text, engine="regex")
    assert result.redacted_text == "[EMAIL_1] [EMAIL_2] and [EMAIL_2]"
    assert result.mapping == {"[EMAIL_2]": "a@b.com"}


@pytest.mark.parametrize(
    "entity",
    [
        engine.Entity("EMAIL", "", 0, 1, 1.0, "regex"),
        engine.Entity("EMAIL", "a", 0, 100, 1.0, "regex"),
        engine.Entity("EMAIL", "wrong", 0, 1, 1.0, "regex"),
    ],
)
def test_invalid_explicit_spans_are_rejected(entity):
    with pytest.raises(ValueError, match="valid ranges"):
        engine.redact("a", [entity])


@pytest.mark.parametrize("algorithm", ["md5", "sha256", "sha3_256"])
def test_hash_algorithm_and_hmac_are_honored(algorithm):
    text = "a@b.com"
    entities = engine.scan(text, engine="regex").entities
    plain = engine.redact(text, entities, strategy="hash", hash_type=algorithm)
    assert hashlib.new(algorithm, text.encode()).hexdigest()[:12] in plain.redacted_text
    key = bytes(range(32))
    keyed = engine.redact(
        text, entities, strategy="hash", hash_type=algorithm, hash_key=key
    )
    assert hmac.new(key, text.encode(), algorithm).hexdigest() in keyed.redacted_text
    assert plain != keyed


def test_invalid_hash_parameters_fail():
    with pytest.raises(ValueError, match="hash_key"):
        engine.redact("text", [], strategy="hash", hash_key=b"short")
    with pytest.raises(ValueError, match="hash_type"):
        engine.redact("text", [], strategy="hash", hash_type="bogus")


@pytest.mark.parametrize("locales", [[""], [1]])
@pytest.mark.parametrize("backend", ["python", "rust"])
def test_invalid_locales_are_consistently_rejected(locales, backend):
    with pytest.raises(ValueError, match="locale"):
        engine.scan("safe", engine="regex", locales=locales, backend=backend)


@pytest.mark.parametrize("locale", ["fr", "en-US"])
def test_fallback_accepts_locale_tags_without_extra_detectors(locale):
    assert engine.scan(
        "a@b.com", engine="regex", locales=[locale], backend="python"
    ).entities


def test_unicode_email_in_fallback():
    result = engine.scan("mail jörg@müller.de", engine="regex", backend="python")
    assert result.entities[0].text == "jörg@müller.de"


@pytest.mark.parametrize(
    "options",
    [
        {"engine": "bogus"},
        {"text_chunk_length": 0},
        {"text_chunk_length": -1},
        {"text_chunk_length": True},
    ],
)
def test_text_service_argument_validation(options):
    with pytest.raises(ValueError):
        TextService(**options)


def test_fallback_adversarial_patterns_complete():
    annotator = RegexAnnotator(locales=["de"])
    for value in [
        "!" * 80000,
        "#a" * 40000,
        "Steuer-ID" + " " * 80000 + "x",
        "Passport" + " " * 80000,
    ]:
        assert not any(annotator.annotate(value).values())


def test_hash_marker_cannot_collide_with_literal_input():
    value = "a@b.com"
    digest = hashlib.sha256(value.encode()).hexdigest()[:12]
    marker = f"[EMAIL_{digest}]"
    text = f"{marker} {value} {value}"
    result = engine.scan_and_redact(text, engine="regex", strategy="hash")
    assert result.mapping == {f"[EMAIL_{digest}_2]": value}
    assert result.redacted_text == f"{marker} [EMAIL_{digest}_2] [EMAIL_{digest}_2]"


@pytest.mark.parametrize(
    "text",
    [
        "?" * 11 + "xiaoming@example.cn",
        '{"note":"email=alice@example.com"}',
        "email = 'dev@example.com'",
        "phone=415-555-2671&email=bob@example.com",
    ],
)
def test_fallback_email_context_is_trimmed_without_losing_mailboxes(text):
    result = engine.scan(text, engine="regex", backend="python", entity_types=["EMAIL"])
    assert len(result.entities) == 1
    assert result.entities[0].text in {
        "xiaoming@example.cn",
        "alice@example.com",
        "dev@example.com",
        "bob@example.com",
    }


def test_spacy_selection_rejects_gliner_only_labels():
    with pytest.raises(ValueError, match="PASSPORT_NUMBER"):
        engine.scan("passport SECRET", engine="spacy", entity_types=["PASSPORT_NUMBER"])


@pytest.mark.parametrize("algorithm", ["md5", "sha256", "sha3_256"])
def test_shared_hash_helper_retains_legacy_widths_and_full_hmac(algorithm):
    value = "a@b.com"
    digest = hashlib.new(algorithm, value.encode()).hexdigest()
    assert engine._hash_value(value, algorithm, None) == digest[:12]
    assert engine._hash_value(value, algorithm, None, plain_length=8) == digest[:8]
    key = bytes(range(32))
    assert (
        engine._hash_value(value, algorithm, key, plain_length=8)
        == hmac.new(key, value.encode(), algorithm).hexdigest()
    )


@pytest.mark.parametrize("mode", ["smart", "spacy", "gliner"])
def test_optional_ner_cannot_remove_overlapping_structured_scan_findings(
    monkeypatch, mode
):
    text = "Ping 127.0.0.1"
    candidates = [engine.Entity("PERSON", text, 0, len(text), 0.8, mode)]
    monkeypatch.setattr(engine, "_spacy_entities", lambda _: candidates)
    monkeypatch.setattr(engine, "_gliner_entities", lambda _: candidates)
    result = engine.scan(text, engine=mode)
    assert any(
        item.type == "IP_ADDRESS" and item.text == "127.0.0.1"
        for item in result.entities
    )
    assert any(item.type == "PERSON" for item in result.entities)
