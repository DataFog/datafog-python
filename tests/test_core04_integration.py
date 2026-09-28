"""Exercise actual Core 0.4 wheels through the Python compatibility adapter.

Examples originate in Core's fixtures/{german,jwt,private-key,npi,
us-routing-number,uuid}.jsonl. Payloads are synthetic detector fixtures,
including a nonfunctional PEM block; no credentials are used.
"""

import importlib.metadata
import re

import pytest

import datafog
from datafog import engine, v5
from datafog.compat import v4

core = pytest.importorskip("datafog_core")

GERMAN = [
    ("DE_IBAN", "DE44 5001 0517 5407 3249 31", "DE44 5001 0517 5407 3249 31"),
    ("DE_VAT_ID", "USt-IdNr DE 123456789 ist gesetzt.", "DE 123456789"),
    ("DE_TAX_ID", "Steuer-ID 12345678901 liegt vor.", "12345678901"),
    (
        "DE_SOCIAL_SECURITY_NUMBER",
        "Rentenversicherungsnummer 65150804A123 liegt vor.",
        "65150804A123",
    ),
    ("DE_POSTAL_CODE", "PLZ10115 Berlin.", "PLZ10115"),
    ("DE_PASSPORT_NUMBER", "Passnummer C12345678 wurde geprueft.", "C12345678"),
    (
        "DE_RESIDENCE_PERMIT_NUMBER",
        "Aufenthaltstitel AT1234567 gueltig.",
        "AT1234567",
    ),
]
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjowfQ.c2ln"
# Deliberately invalid key material: the payload decodes to ASCII "abcd".
PRIVATE_KEY = (
    "-----BEGIN PRIVATE KEY-----\nYWJjZA==\n-----END PRIVATE KEY-----"  # gitleaks:allow
)
UUID = "550e8400-e29b-11d4-a716-446655440000"
NEW_DEFAULTS = [
    ("JWT", JWT, JWT),
    ("PRIVATE_KEY", PRIVATE_KEY, PRIVATE_KEY),
    ("NPI", "NPI 1234567893", "1234567893"),
    ("US_ROUTING_NUMBER", "routing 021000021", "021000021"),
]
COMPAT_NEW_DEFAULTS = [sample for sample in NEW_DEFAULTS if sample[0] != "NPI"]


def test_supported_wheel_version_and_capability_contract():
    version = importlib.metadata.version("datafog-core")
    assert version.split(".")[:2] == ["0", "4"], version
    capabilities = core.capabilities()
    assert capabilities["contract_version"] == 1
    supported = capabilities["supported_entities"]
    defaults = capabilities["default_entities"]
    assert supported == sorted(set(supported))
    assert defaults == sorted(set(defaults))
    assert set(defaults) <= set(supported)
    assert {label for label, _, _ in NEW_DEFAULTS} <= set(defaults)
    assert "PERSON" in supported and "PERSON" not in defaults
    assert "UUID" in supported and "UUID" not in defaults
    assert capabilities["entities"]["PERSON"]["scopes"] == ["structured"]
    assert capabilities["entities"]["UUID"]["activation"]["scan_config"] == {
        "detect_uuid": True
    }
    german_labels = {label for label, _, _ in GERMAN}
    assert not german_labels & set(defaults)
    for locale in ("de", "de-DE", "de_DE"):
        assert german_labels <= set(capabilities["locales"][locale]["enabled_entities"])


@pytest.mark.parametrize("label, sample, value", COMPAT_NEW_DEFAULTS)
@pytest.mark.parametrize("explicit_selection", [False, True])
def test_new_default_entities_survive_adapter_and_redaction(
    label, sample, value, explicit_selection
):
    text = "😀 café\n" + sample
    options = {"backend": "rust"}
    if explicit_selection:
        options["entity_types"] = [label]
    result = datafog.scan(text, **options)
    assert type(result) is v4.ScanResult
    matches = [item for item in result.entities if item.type == label]
    assert len(matches) == 1
    item = matches[0]
    assert type(item) is v4.Entity
    assert item.text == text[item.start : item.end] == value
    redacted = datafog.redact(text, **options)
    assert type(redacted) is v4.RedactResult
    assert redacted.redacted_text == text.replace(value, f"[{label}_1]")


@pytest.mark.parametrize("label, sample, value", GERMAN)
@pytest.mark.parametrize("activation", ["locale", "selection"])
def test_seven_german_entities_activate_and_redact(label, sample, value, activation):
    text = "😀 München " + sample
    assert not any(
        item.type == label for item in datafog.scan(text, backend="rust").entities
    )
    options = {"backend": "rust"}
    if activation == "locale":
        options["locales"] = ["de"]
    else:
        options["entity_types"] = [label]
    result = datafog.scan(text, **options)
    matches = [item for item in result.entities if item.type == label]
    assert len(matches) == 1
    item = matches[0]
    assert item.text == text[item.start : item.end] == value
    assert datafog.redact(text, **options).redacted_text == text.replace(
        value, f"[{label}_1]"
    )


def test_uuid_optin_selection_drives_native_configuration():
    text = "😀 café " + UUID
    assert "UUID" not in {
        item.type for item in datafog.scan(text, backend="rust").entities
    }
    options = {"backend": "rust", "entity_types": ["UUID"]}
    matches = datafog.scan(text, **options).entities
    assert [(item.type, item.text) for item in matches] == [("UUID", UUID)]
    assert text[matches[0].start : matches[0].end] == UUID
    assert datafog.redact(text, **options).redacted_text == "😀 café [UUID_1]"


@pytest.mark.parametrize("locale", ["de", "de-DE", "de_DE", " DE-dE\t"])
def test_real_german_aliases(locale):
    sample = GERMAN[0][1]
    matches = datafog.scan(sample, locales=[locale], backend="rust").entities
    assert [(item.type, item.text) for item in matches] == [("DE_IBAN", sample)]


def test_plural_locales_union_without_duplicate_redactions():
    text = "😀 a@example.com " + GERMAN[0][1]
    options = {"locales": ["fr", "de_DE", "en-US", "de", "de"], "backend": "rust"}
    matches = datafog.scan(text, **options).entities
    assert [(item.type, item.text) for item in matches] == [
        ("EMAIL", "a@example.com"),
        ("DE_IBAN", GERMAN[0][1]),
    ]
    assert datafog.redact(text, **options).redacted_text == "😀 [EMAIL_1] [DE_IBAN_1]"


@pytest.mark.parametrize("label, sample, value", COMPAT_NEW_DEFAULTS + GERMAN)
def test_new_labels_respect_existing_selection_and_allowlists(label, sample, value):
    text = "😀\n" + sample
    options = {"entity_types": [label], "backend": "rust"}
    assert [item.text for item in datafog.scan(text, **options).entities] == [value]
    assert not datafog.scan(text, allowlist=[value], **options).entities
    assert not datafog.scan(
        text, allowlist_patterns=[re.escape(value)], **options
    ).entities
    assert datafog.redact(text, allowlist=[value], **options).redacted_text == text


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_native_findings_use_legacy_transformations(strategy):
    text = "😀 " + GERMAN[0][1] + " and " + UUID
    options = {"entity_types": ["DE_IBAN", "UUID"], "backend": "rust"}
    scanned = datafog.scan(text, **options)
    assert [item.type for item in scanned.entities] == ["DE_IBAN", "UUID"]
    expected = engine.redact(text, scanned.entities, strategy=strategy)
    assert datafog.redact(text, strategy=strategy, **options) == expected


@pytest.mark.parametrize(
    "label, raw", [("NPI", "1234567893"), ("US_ROUTING_NUMBER", "021000021")]
)
def test_contextual_identifiers_do_not_activate_without_context(label, raw):
    result = datafog.scan(raw, entity_types=[label], backend="rust")
    assert not result.entities


def test_npi_retains_native_identity_but_legacy_overlap_prefers_phone():
    """4.x suppresses overlaps before selection; this is a reviewed difference."""
    text = "😀 café NPI 1234567893"
    native = v5.scan(text)
    assert [(item.entity_type, item.matched_text) for item in native] == [
        ("PHONE", "1234567893"),
        ("NPI", "1234567893"),
    ]
    assert {
        (item.codepoint_range.start, item.codepoint_range.end) for item in native
    } == {(11, 21)}
    legacy = datafog.scan(text, backend="rust")
    assert [(item.type, item.text) for item in legacy.entities] == [
        ("PHONE", "1234567893")
    ]
    assert not datafog.scan(text, entity_types=["NPI"], backend="rust").entities
    assert datafog.redact(text, backend="rust").redacted_text == "😀 café NPI [PHONE_1]"
    # Native selection occurs before transformation overlap resolution, exposing
    # the NPI-specific route without changing the 4.x compatibility contract.
    result = v5.scan_and_transform(
        text,
        {"transform": {"default": {"strategy": "redact"}, "entities": ["NPI"]}},
    )
    assert result.text == "😀 café NPI [NPI]"


def test_structured_only_person_rejected_by_text_adapter():
    with pytest.raises(ValueError, match="PERSON"):
        datafog.scan("Jane Doe", entity_types=["PERSON"], backend="rust")


def test_unsupported_locale_rejected_explicitly():
    with pytest.raises(ValueError, match="locale"):
        datafog.scan("a@example.com", locales=["unsupported"], backend="rust")


def test_python_default_backend_remains_unchanged():
    assert not datafog.scan(JWT).entities
    assert [item.type for item in datafog.scan(JWT, backend="rust").entities] == ["JWT"]
