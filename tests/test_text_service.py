"""Public TextService behavior using the shipped service and shared engine."""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from datafog import engine
from datafog.services.text_service import TextService


@pytest.mark.parametrize(
    "options",
    [{"engine": "invalid"}, {"text_chunk_length": 0}, {"text_chunk_length": -1}],
)
def test_invalid_configuration_is_explicit(options):
    with pytest.raises(ValueError):
        TextService(**options)


def test_default_service_detects_native_only_entities():
    result = TextService().annotate_text_sync("card 6011111111111117 ip 2001:db8::1")
    assert result == {
        "CREDIT_CARD": ["6011111111111117"],
        "IP_ADDRESS": ["2001:db8::1"],
    }


def test_long_document_seams_preserve_complete_entities():
    value = "john@example.com"
    text = "x" * 995 + " " + value + " " + "y" * 1010 + " ssn 123-45-6789"
    result = TextService(text_chunk_length=1000).annotate_text_sync(text)
    assert result == {"EMAIL": [value], "SSN": ["123-45-6789"]}


def test_structured_output_preserves_unicode_source_ranges():
    text = "😀 café john@example.com and john@example.com"
    result = TextService(text_chunk_length=10).annotate_text_sync(text, structured=True)
    assert len(result) == 2
    assert all(
        item.label == "EMAIL" and text[item.start : item.end] == item.text
        for item in result
    )
    assert result[0].start < result[1].start


def test_batch_results_preserve_input_order_and_duplicate_documents():
    texts = ["a@example.com", "no pii", "a@example.com"]
    assert TextService().batch_annotate_text_sync(texts) == [
        {"EMAIL": ["a@example.com"]},
        {},
        {"EMAIL": ["a@example.com"]},
    ]


@pytest.mark.asyncio
async def test_async_results_match_synchronous_service():
    service = TextService()
    texts = ["a@example.com", "ssn 123-45-6789", "no pii"]
    assert await service.batch_annotate_text_async(
        texts
    ) == service.batch_annotate_text_sync(texts)
    assert await service.annotate_text_async(
        texts[0], structured=True
    ) == service.annotate_text_sync(texts[0], structured=True)


@pytest.mark.asyncio
async def test_async_detection_runs_outside_event_loop_thread(monkeypatch):
    loop_thread = threading.get_ident()
    worker_threads = []

    def detect(text, **_):
        worker_threads.append(threading.get_ident())
        return SimpleNamespace(entities=[])

    monkeypatch.setattr(engine, "scan", detect)
    await asyncio.wait_for(TextService().annotate_text_async("text"), timeout=2)
    assert worker_threads and all(thread != loop_thread for thread in worker_threads)


@pytest.mark.parametrize("mode", ["auto", "smart"])
def test_optional_ner_adds_to_structured_findings(monkeypatch, mode):
    text = "Ann owns 6011111111111117"
    monkeypatch.setattr(
        engine,
        "_gliner_entities",
        lambda _: [engine.Entity("PERSON", "Ann", 0, 3, 0.8, "gliner")],
    )
    result = TextService(engine=mode).annotate_text_sync(text)
    assert result == {"PERSON": ["Ann"], "CREDIT_CARD": ["6011111111111117"]}


def test_custom_gliner_model_is_forwarded(monkeypatch):
    models = []

    def detect(_, model_name):
        models.append(model_name)
        return []

    monkeypatch.setattr(engine, "_gliner_entities", detect)
    assert (
        TextService(engine="smart", gliner_model="local/custom").annotate_text_sync(
            "no pii"
        )
        == {}
    )
    assert models == ["local/custom"]


def test_locale_activates_additional_shared_detectors():
    text = "Aufenthaltstitel AT1234567 gueltig."
    assert TextService(locales=["de"]).annotate_text_sync(text) == {
        "DE_RESIDENCE_PERMIT_NUMBER": ["AT1234567"]
    }


def test_empty_and_invalid_text():
    service = TextService()
    assert service.annotate_text_sync("") == {}
    assert service.annotate_text_sync("", structured=True) == []
    with pytest.raises(TypeError, match="text must be a string"):
        service.annotate_text_sync(None)
