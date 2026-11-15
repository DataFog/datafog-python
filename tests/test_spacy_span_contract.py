"""Optional real-spaCy offset integration without downloading model weights."""

import pytest

from datafog import engine
from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
from datafog.services.text_service import TextService

spacy = pytest.importorskip("spacy")


@pytest.fixture
def real_annotator(monkeypatch):
    nlp = spacy.blank("en")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns(
        [
            {"label": "PERSON", "pattern": "Ann"},
            {"label": "ORG", "pattern": "Acme Corp"},
            {"label": "DATE", "pattern": "yesterday"},
        ]
    )
    annotator = SpacyPIIAnnotator(nlp=nlp, model_name="local-test-ruler")
    monkeypatch.setattr(engine, "_get_spacy_annotator", lambda: annotator)
    return annotator


def test_spacy_ranges_redact_actual_name_without_hitting_prefix(real_annotator):
    text = "Annual report by Ann yesterday: 6011111111111117"
    result = engine.scan_and_redact(text, engine="spacy")
    assert (
        result.redacted_text == "Annual report by [PERSON_1] yesterday: [CREDIT_CARD_1]"
    )
    assert all(text[item.start : item.end] == item.text for item in result.entities)


def test_spacy_service_combines_ner_and_native_detection(real_annotator):
    text = "Ann at Acme Corp: 6011111111111117 ip 2001:db8::1"
    service = TextService(engine="spacy")
    result = service.annotate_text_sync(text)
    assert result == {
        "PERSON": ["Ann"],
        "ORGANIZATION": ["Acme Corp"],
        "CREDIT_CARD": ["6011111111111117"],
        "IP_ADDRESS": ["2001:db8::1"],
    }
    assert all(
        text[item.start : item.end] == item.text
        for item in service.annotate_text_sync(text, structured=True)
    )


def test_spacy_repeated_names_keep_each_original_span(real_annotator):
    text = "Ann wrote an Annual report for Ann."
    result = engine.scan(text, engine="spacy")
    assert [(item.start, item.end) for item in result.entities] == [(0, 3), (31, 34)]
