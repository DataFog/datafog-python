"""The Rust compatibility adapter follows installed Core capabilities.

These tests use a small synthetic registry, not a copy of Core's entity list.
Real candidate-wheel coverage lives separately in the native contract suite.
"""

import copy
import sys
from types import SimpleNamespace

import pytest

import datafog
from datafog import engine
from datafog.compat import v4


def capability_fixture():
    def entity(kind="default", config=None, scopes=None):
        activation = {"kind": kind}
        if config is not None:
            activation["scan_config"] = config
        return {
            "scopes": scopes or ["structured", "text"],
            "activation": activation,
        }

    entities = {
        "EMAIL": entity(),
        "FUTURE_ID": entity(),
        "UUID": entity("config", {"detect_uuid": True}),
        "FUTURE_OPTIN": entity("config", {"detect_future": True}),
        "DE_IBAN": entity("locale", {"locale": "de"}),
        "FUTURE_LOCAL": entity("locale", {"locale": "zz"}),
        "PERSON": entity("structured", scopes=["structured"]),
    }
    return {
        "contract_version": 1,
        "supported_entities": sorted(entities),
        "default_entities": ["EMAIL", "FUTURE_ID"],
        "locales": {
            "de": {"enabled_entities": ["DE_IBAN"]},
            "de-DE": {"enabled_entities": ["DE_IBAN"]},
            "de_DE": {"enabled_entities": ["DE_IBAN"]},
            "en-US": {"enabled_entities": []},
            "fr": {"enabled_entities": []},
            "zz": {"enabled_entities": ["FUTURE_LOCAL"]},
        },
        "entities": entities,
    }


def finding(text, value, label, start=None):
    start = text.index(value) if start is None else start
    return SimpleNamespace(
        entity_type=label,
        matched_text=value,
        codepoint_range=SimpleNamespace(start=start, end=start + len(value)),
        byte_range=SimpleNamespace(
            start=len(text[:start].encode()),
            end=len(text[: start + len(value)].encode()),
        ),
    )


@pytest.fixture
def core(monkeypatch):
    state = SimpleNamespace(
        metadata=capability_fixture(), calls=[], findings=[], response=None
    )

    def scan(text, config=None):
        state.calls.append((text, copy.deepcopy(config)))
        if state.response:
            return state.response(text, config)
        return state.findings

    state.module = SimpleNamespace(
        capabilities=lambda: copy.deepcopy(state.metadata), scan=scan
    )
    monkeypatch.setitem(sys.modules, "datafog_core", state.module)
    return state


def test_default_scan_leaves_optin_configuration_disabled(core):
    datafog.scan("safe text", backend="rust")
    assert len(core.calls) == 1
    assert not core.calls[0][1].get("detect_uuid", False)
    assert not core.calls[0][1].get("detect_future", False)
    assert not core.calls[0][1].get("locale")


@pytest.mark.parametrize("label", ["FUTURE_ID", "UNADVERTISED_FUTURE"])
def test_future_findings_preserve_legacy_classes_and_unicode_offsets(core, label):
    text = "😀 München opaque-secret"
    native = finding(text, "opaque-secret", label)
    assert native.byte_range.start != native.codepoint_range.start
    core.findings = [native]
    result = datafog.scan(text, backend="rust")
    assert type(result) is v4.ScanResult is engine.ScanResult
    assert type(result.entities[0]) is v4.Entity is engine.Entity
    item = result.entities[0]
    assert item.type == label
    assert text[item.start : item.end] == item.text == "opaque-secret"
    assert item.engine == "regex" and item.confidence == 1.0
    redacted = datafog.redact(text, backend="rust")
    assert type(redacted) is v4.RedactResult is engine.RedactResult
    assert redacted.redacted_text == f"😀 München [{label}_1]"


@pytest.mark.parametrize(
    "label, expected",
    [("UUID", {"detect_uuid": True}), ("FUTURE_OPTIN", {"detect_future": True})],
)
def test_explicit_config_activation_is_metadata_driven(core, label, expected):
    datafog.scan("value", entity_types=[label.lower()], backend="rust")
    assert len(core.calls) == 1
    assert all(core.calls[0][1][key] == value for key, value in expected.items())


@pytest.mark.parametrize("label, locale", [("DE_IBAN", "de"), ("FUTURE_LOCAL", "zz")])
def test_explicit_entity_selection_activates_its_advertised_locale(core, label, locale):
    datafog.scan("value", entity_types=[label], backend="rust")
    assert any(config.get("locale") == locale for _, config in core.calls)


@pytest.mark.parametrize("supplied", [" DE-dE \t", "DE_de", "DE", " FR "])
def test_locale_aliases_match_capabilities_and_preserve_source(core, supplied):
    datafog.scan("value", locales=[supplied], backend="rust")
    assert core.calls == [("value", {"locale": supplied})]


def test_single_string_locale_remains_supported(core):
    datafog.scan("value", locales="de", backend="rust")
    assert core.calls == [("value", {"locale": "de"})]


def test_plural_locales_union_and_deduplicate_findings_in_document_order(core):
    text = "mail german other"

    def response(text, config):
        matches = [finding(text, "mail", "EMAIL")]
        if config["locale"] == "de":
            matches.append(finding(text, "german", "DE_IBAN"))
        if config["locale"] == "zz":
            matches.insert(0, finding(text, "other", "FUTURE_LOCAL"))
        return matches

    core.response = response
    result = datafog.scan(text, locales=["zz", "de", "de"], backend="rust")
    assert {config["locale"] for _, config in core.calls} == {"de", "zz"}
    assert [(item.type, item.start) for item in result.entities] == [
        ("EMAIL", 0),
        ("DE_IBAN", 5),
        ("FUTURE_LOCAL", 12),
    ]


def test_config_activation_applies_to_each_locale_scan(core):
    datafog.scan("value", entity_types=["UUID"], locales=["de", "zz"], backend="rust")
    assert {config["locale"] for _, config in core.calls} == {"de", "zz"}
    assert all(config["detect_uuid"] is True for _, config in core.calls)


def test_requested_locale_and_entity_activation_are_combined(core):
    datafog.scan("value", entity_types=["DE_IBAN"], locales=["zz"], backend="rust")
    assert {config["locale"] for _, config in core.calls} == {"de", "zz"}


def test_structured_only_selection_rejected_before_scan(core):
    with pytest.raises(ValueError, match="PERSON"):
        datafog.scan("value", entity_types=["PERSON"], backend="rust")
    assert not core.calls


def test_unsupported_locale_rejected_before_scan(core):
    with pytest.raises(ValueError, match="locale"):
        datafog.scan("value", locales=["unsupported"], backend="rust")
    assert not core.calls


@pytest.mark.parametrize("capabilities", [None, {}, "not callable"])
def test_missing_capability_api_fails_actionably(core, capabilities):
    core.module.capabilities = capabilities
    with pytest.raises(RuntimeError, match="capabilit|contract|Core|core"):
        datafog.scan("value", backend="rust")
    assert not core.calls


@pytest.mark.parametrize("version", [2, "1", None, True])
def test_invalid_contract_version_rejected(core, version):
    core.metadata["contract_version"] = version
    with pytest.raises(RuntimeError, match="contract|capabilit"):
        datafog.scan("value", backend="rust")
    assert not core.calls


@pytest.mark.parametrize(
    "field",
    [
        "contract_version",
        "supported_entities",
        "default_entities",
        "locales",
        "entities",
    ],
)
def test_missing_required_adapter_metadata_rejected(core, field):
    del core.metadata[field]
    with pytest.raises(RuntimeError, match="capabilit|contract"):
        datafog.scan("value", backend="rust")
    assert not core.calls


@pytest.mark.parametrize(
    "field, value",
    [
        ("supported_entities", "EMAIL"),
        ("default_entities", ["UNSUPPORTED"]),
        ("locales", {"de": {"enabled_entities": ["UNSUPPORTED"]}}),
        ("entities", []),
    ],
)
def test_malformed_capability_inventory_rejected(core, field, value):
    core.metadata[field] = value
    with pytest.raises(RuntimeError, match="capabilit"):
        datafog.scan("value", backend="rust")
    assert not core.calls


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {"scopes": "text", "activation": {"kind": "default"}},
        {"scopes": ["text"]},
        {"scopes": ["text"], "activation": {"kind": "future-kind"}},
        {"scopes": ["text"], "activation": {"kind": "config"}},
        {
            "scopes": ["text"],
            "activation": {"kind": "locale", "scan_config": {"other": True}},
        },
    ],
)
def test_incomplete_selected_entity_activation_rejected(core, metadata):
    core.metadata["entities"]["FUTURE_ID"] = metadata
    with pytest.raises(RuntimeError, match="capabilit"):
        datafog.scan("value", entity_types=["FUTURE_ID"], backend="rust")
    assert not core.calls


def test_conflicting_activation_configuration_rejected_without_partial_scan(core):
    core.metadata["entities"]["FUTURE_OPTIN"]["activation"]["scan_config"] = {
        "detect_uuid": False
    }
    with pytest.raises(RuntimeError, match="conflicting"):
        datafog.scan("value", entity_types=["UUID", "FUTURE_OPTIN"], backend="rust")
    assert not core.calls


def test_locale_normalization_does_not_strip_non_ascii_whitespace(core):
    with pytest.raises(ValueError, match="locale"):
        datafog.scan("value", locales=["\u00a0de\u00a0"], backend="rust")
    assert not core.calls


def test_additive_metadata_does_not_break_compatible_contract(core):
    core.metadata["future_metadata"] = {"anything": True}
    core.metadata["entities"]["EMAIL"]["future_field"] = 42
    datafog.scan("value", backend="rust")
    assert core.calls


def test_capability_errors_propagate_without_fallback(core):
    failure = OSError("registry unavailable")

    def fail():
        raise failure

    core.module.capabilities = fail
    with pytest.raises(OSError) as caught:
        datafog.scan("value", backend="rust")
    assert caught.value is failure
    assert not core.calls


def test_native_scan_errors_propagate_without_fallback(core):
    failure = RuntimeError("native scan failed")

    def fail(text, config):
        raise failure

    core.response = fail
    with pytest.raises(RuntimeError) as caught:
        datafog.scan("value", backend="rust")
    assert caught.value is failure


@pytest.mark.parametrize("strategy", ["token", "mask", "hash", "pseudonymize"])
def test_future_labels_preserve_filter_allowlist_and_redaction_behavior(core, strategy):
    text = "keep secret a@example.com secret"
    core.findings = [
        finding(text, "keep", "FUTURE_ID"),
        finding(text, "secret", "FUTURE_ID", 5),
        finding(text, "a@example.com", "EMAIL"),
        finding(text, "secret", "FUTURE_ID", 26),
    ]
    options = {
        "entity_types": ["future_id"],
        "allowlist": ["keep"],
        "backend": "rust",
    }
    result = datafog.scan(text, **options)
    assert [item.text for item in result.entities] == ["secret", "secret"]
    expected = engine.redact(text, result.entities, strategy=strategy)
    assert datafog.redact(text, strategy=strategy, **options) == expected
    assert not datafog.scan(text, allowlist_patterns=[r"secret"], **options).entities


def test_capability_reader_cached_and_replacement_invalidates(core):
    reads = []

    def read():
        reads.append(1)
        return core.metadata

    core.module.capabilities = read
    datafog.scan("safe", backend="rust")
    datafog.scan("safe", backend="rust")
    assert reads == [1]

    def replacement():
        reads.append(2)
        return core.metadata

    core.module.capabilities = replacement
    datafog.scan("safe", backend="rust")
    assert reads == [1, 2]


@pytest.mark.parametrize("failure", ["exception", "version", "locale"])
def test_failed_capability_reads_are_not_cached(core, failure):
    reads = []

    def read():
        reads.append(1)
        if len(reads) == 1:
            if failure == "exception":
                raise RuntimeError("temporary read failure")
            broken = copy.deepcopy(core.metadata)
            if failure == "version":
                broken["contract_version"] = 999
            else:
                broken["locales"]["de"]["enabled_entities"] = ["NOT_SUPPORTED"]
            return broken
        return core.metadata

    core.module.capabilities = read
    with pytest.raises(RuntimeError):
        datafog.scan("safe", backend="rust")
    datafog.scan("safe", backend="rust")
    assert reads == [1, 1]


def test_cached_snapshot_and_nested_configs_are_private(core):
    core.metadata["entities"]["FUTURE_OPTIN"]["activation"]["scan_config"] = {
        "future_options": {"enabled": ["original"]}
    }
    core.module.capabilities = lambda: core.metadata

    def mutate_config(text, config):
        config["future_options"]["enabled"].append("native mutation")
        return []

    core.response = mutate_config
    datafog.scan(
        "safe", backend="rust", entity_types=["FUTURE_OPTIN"], locales=["de", "fr"]
    )
    core.metadata["entities"]["FUTURE_OPTIN"]["activation"]["scan_config"][
        "future_options"
    ]["enabled"].append("caller mutation")
    datafog.scan("safe", backend="rust", entity_types=["FUTURE_OPTIN"])
    assert len(core.calls) == 3
    assert all(
        config["future_options"]["enabled"] == ["original"] for _, config in core.calls
    )
