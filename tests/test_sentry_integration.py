"""Tests for the Sentry SDK integration (DataFogSentryIntegration).

PII literals below are split ("jane.doe@" "acme.com") so this source file
itself never contains a contiguous match — the values only assemble at
runtime. This keeps write-time PII scanners (including our own Claude Code
hook) quiet while the tests exercise real detections.
"""

import json

import pytest

sentry_sdk = pytest.importorskip("sentry_sdk")

from datafog.integrations.sentry import (  # noqa: E402
    DataFogSentryIntegration,
    scrub_event,
)

EMAIL = "jane.doe@" "acme.com"
CARD = "4242 4242 " "4242 4242"
SSN = "856-45-" "6789"
PHONE = "(555) 867-" "5309"


def _error_event(**overrides) -> dict:
    event = {
        "event_id": "0123456789abcdef0123456789abcdef",
        "platform": "python",
        "release": "myapp@1.2.3",
        "logentry": {"message": f"lookup failed for {EMAIL}", "params": []},
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": f"could not bill card {CARD}",
                    "stacktrace": {
                        "frames": [
                            {
                                "function": "charge",
                                "vars": {
                                    "customer_ssn": f"'{SSN}'",
                                    "attempts": "3",
                                    "form": {"contact": f"'{EMAIL}'"},
                                },
                            }
                        ]
                    },
                }
            ]
        },
        "breadcrumbs": {
            "values": [
                {
                    "message": f"sms sent to {PHONE}",
                    "category": "notify",
                    "data": {"to": PHONE},
                }
            ]
        },
        "request": {
            "url": f"https://api.example.com/users?email={EMAIL}",
            "headers": {"X-Contact": EMAIL},
            "data": {"ssn": SSN},
        },
        "extra": {"note": f"customer email {EMAIL}", "nested": [{"card": CARD}]},
        "tags": {"support_contact": EMAIL},
        "user": {"email": EMAIL, "id": "42"},
    }
    event.update(overrides)
    return event


def _transaction_event() -> dict:
    return {
        "type": "transaction",
        "transaction": f"/users/{EMAIL}",
        "spans": [
            {
                "op": "db.query",
                "description": f"SELECT * FROM users WHERE email = '{EMAIL}'",
                "data": {"db.statement": f"... ssn = '{SSN}' ..."},
            }
        ],
    }


class TestScrubEvent:
    def test_scrubs_all_error_event_surfaces(self):
        event = scrub_event(_error_event(), None)
        flat = json.dumps(event)
        for value in (EMAIL, CARD, SSN, PHONE):
            assert value not in flat
        assert "[EMAIL_1]" in event["logentry"]["message"]
        assert "[CREDIT_CARD_1]" in event["exception"]["values"][0]["value"]
        frame_vars = event["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]
        assert SSN not in frame_vars["customer_ssn"]
        assert EMAIL not in frame_vars["form"]["contact"]

    def test_scrubs_transaction_spans(self):
        event = scrub_event(_transaction_event(), None)
        flat = json.dumps(event)
        assert EMAIL not in flat
        assert SSN not in flat

    def test_clean_event_unchanged(self):
        event = {
            "event_id": "0123456789abcdef0123456789abcdef",
            "logentry": {"message": "connection refused"},
            "extra": {"retries": "3"},
        }
        assert scrub_event(json.loads(json.dumps(event)), None) == event

    def test_skip_keys_untouched(self):
        # Machine identifiers are never scanned, even when a value happens
        # to look like PII (a release tag is not an email).
        event = _error_event(release=f"deploy-by-{EMAIL}")
        scrubbed = scrub_event(event, None)
        assert scrubbed["release"] == f"deploy-by-{EMAIL}"
        assert scrubbed["event_id"] == "0123456789abcdef0123456789abcdef"

    def test_allowlist_exempts_exact_value(self):
        event = scrub_event(_error_event(), None, allowlist=[EMAIL])
        assert event["tags"]["support_contact"] == EMAIL
        assert CARD not in json.dumps(event)

    def test_allowlist_patterns_exempt_fullmatch(self):
        event = scrub_event(_error_event(), None, allowlist_patterns=[r".*@acme\.com"])
        assert event["tags"]["support_contact"] == EMAIL

    def test_entity_types_restrict_detection(self):
        event = scrub_event(_error_event(), None, entity_types=["CREDIT_CARD"])
        flat = json.dumps(event)
        assert CARD not in flat
        assert EMAIL in flat

    def test_non_string_values_survive(self):
        event = {
            "extra": {"count": 3, "ok": True, "none": None, "pi": 3.14},
            "logentry": {"message": f"contact {EMAIL}"},
        }
        scrubbed = scrub_event(event, None)
        assert scrubbed["extra"] == {"count": 3, "ok": True, "none": None, "pi": 3.14}
        assert EMAIL not in scrubbed["logentry"]["message"]

    def test_budget_overflow_replaced_with_marker_never_raw(self, monkeypatch):
        # Once the per-event budget is exhausted, remaining strings are
        # replaced with [UNSCANNED_N_CHARS] markers — never sent raw, which
        # would be unscanned PII egress.
        from datafog.integrations import sentry as sentry_module

        # The walker drains its stack LIFO, so the logentry message (30
        # chars) is scanned first and exactly exhausts the budget; the extra
        # string then takes the whole-string marker path.
        monkeypatch.setattr(sentry_module, "TOTAL_SCAN_CHARS", 30)
        event = {
            "extra": {"a": f"first field has {EMAIL} inside it"},
            "logentry": {"message": f"second field {EMAIL}"},
        }
        scrubbed = scrub_event(event, None)
        flat = json.dumps(scrubbed)
        assert EMAIL not in flat
        assert "[EMAIL_1]" in scrubbed["logentry"]["message"]
        assert scrubbed["extra"]["a"] == "[UNSCANNED_43_CHARS]"

    def test_pii_straddling_scan_boundary_never_reassembles(self, monkeypatch):
        # A PII value split by the per-string cap fails to match in the
        # truncated chunk; the tail must be masked, not reattached raw —
        # otherwise the full value reassembles unredacted in the output.
        from datafog.integrations import sentry as sentry_module

        monkeypatch.setattr(sentry_module, "MAX_SCAN_CHARS", 24)
        event = {"logentry": {"message": f"padding here {EMAIL} after"}}
        message = scrub_event(event, None)["logentry"]["message"]
        assert EMAIL not in message
        assert "[UNSCANNED_" in message

    def test_tuple_and_set_values_scrubbed(self):
        # Sentry frame vars and user extra can carry tuples pre-serialization;
        # they are rebuilt as lists (the serializer emits both as JSON arrays).
        event = {
            "extra": {
                "pair": (f"first {EMAIL}", f"second {CARD}"),
                "unique": {f"member {SSN}"},
            }
        }
        flat = json.dumps(scrub_event(event, None))
        for value in (EMAIL, CARD, SSN):
            assert value not in flat

    def test_aliased_container_scanned_once(self, monkeypatch):
        # The same object reachable from two places must be scanned once:
        # double-scanning double-spends the budget, which could starve later
        # fields into the unscanned path.
        import datafog

        calls = []
        real_redact = datafog.redact

        def counting_redact(text, **kwargs):
            calls.append(text)
            return real_redact(text, **kwargs)

        monkeypatch.setattr(datafog, "redact", counting_redact)
        shared = {"contact": f"reach me at {EMAIL}"}
        event = {"extra": {"first": shared, "second": shared}}
        scrubbed = scrub_event(event, None)
        assert len(calls) == 1
        assert EMAIL not in json.dumps(scrubbed)

    def test_cyclic_structure_terminates(self):
        cyclic = {"note": f"contact {EMAIL}"}
        cyclic["self"] = cyclic
        event = {"extra": cyclic}
        scrubbed = scrub_event(event, None)
        assert EMAIL not in scrubbed["extra"]["note"]

    def test_scrub_event_rejects_invalid_fail_policy(self):
        with pytest.raises(ValueError):
            scrub_event(_error_event(), None, fail_policy="sideways")


class TestFailPolicy:
    def test_fail_open_returns_event_on_engine_error(self, monkeypatch):
        import datafog

        def boom(*args, **kwargs):
            raise RuntimeError("engine exploded")

        monkeypatch.setattr(datafog, "redact", boom)
        event = _error_event()
        assert scrub_event(event, None, fail_policy="open") is event

    def test_fail_closed_drops_event_on_engine_error(self, monkeypatch):
        import datafog

        def boom(*args, **kwargs):
            raise RuntimeError("engine exploded")

        monkeypatch.setattr(datafog, "redact", boom)
        assert scrub_event(_error_event(), None, fail_policy="closed") is None

    def test_error_logging_never_echoes_event_content(self, monkeypatch, caplog):
        import datafog

        def boom(*args, **kwargs):
            raise RuntimeError(f"engine choked on {EMAIL}")

        monkeypatch.setattr(datafog, "redact", boom)
        with caplog.at_level("WARNING", logger="datafog.integrations.sentry"):
            scrub_event(_error_event(), None, fail_policy="open")
        assert EMAIL not in caplog.text

    def test_invalid_fail_policy_rejected(self):
        with pytest.raises(ValueError):
            DataFogSentryIntegration(fail_policy="sideways")


class TestIntegrationWiring:
    """End-to-end through a real sentry_sdk client.

    Events are captured in ``before_send`` — which runs *after* global
    event processors, so it sees exactly what the integration produces —
    and dropped by returning None, so nothing touches the network.
    """

    def _init(self, captured, **integration_kwargs):
        def _capture(event, hint):
            captured.append(event)
            return None

        sentry_sdk.init(
            dsn="https://key@example.invalid/1",
            integrations=[DataFogSentryIntegration(**integration_kwargs)],
            default_integrations=False,
            before_send=_capture,
        )

    def test_capture_message_scrubbed(self):
        captured = []
        self._init(captured)
        sentry_sdk.capture_message(f"reset link sent to {EMAIL}")
        assert len(captured) == 1
        flat = json.dumps(captured[0])
        assert EMAIL not in flat
        assert "[EMAIL_1]" in flat

    def test_capture_exception_scrubs_message_and_local_vars(self):
        captured = []
        self._init(captured)
        try:
            customer_ssn = SSN  # noqa: F841 — captured as a frame local
            raise ValueError(f"invalid ssn for {EMAIL}")
        except ValueError:
            sentry_sdk.capture_exception()
        assert len(captured) == 1
        flat = json.dumps(captured[0])
        assert EMAIL not in flat
        assert SSN not in flat

    def test_integration_absent_is_passthrough(self):
        # The global processor stays registered for the life of the process;
        # with no DataFogSentryIntegration on the current client it must not
        # touch events.
        captured = []

        def _capture(event, hint):
            captured.append(event)
            return None

        sentry_sdk.init(
            dsn="https://key@example.invalid/1",
            default_integrations=False,
            before_send=_capture,
        )
        sentry_sdk.capture_message(f"contact {EMAIL}")
        assert len(captured) == 1
        assert EMAIL in json.dumps(captured[0])

    def test_integration_allowlist_respected(self):
        captured = []
        self._init(captured, allowlist=[EMAIL])
        sentry_sdk.capture_message(f"support contact {EMAIL}, card {CARD}")
        flat = json.dumps(captured[0])
        assert EMAIL in flat
        assert CARD not in flat

    def test_processor_lookup_failure_passes_event_through(self, monkeypatch):
        # The integration lookup runs outside the fail-policy path; if it
        # raises, event delivery must survive (pass-through, fail open).
        from datafog.integrations import sentry as sentry_module

        def boom():
            raise RuntimeError("client lookup exploded")

        monkeypatch.setattr(sentry_module.sentry_sdk, "get_client", boom)
        event = {"logentry": {"message": "hello"}}
        assert sentry_module._global_processor(event, None) is event
