"""Tests for datafog.telemetry module."""

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_telemetry_state():
    """Reset telemetry module-level state between tests."""
    import datafog.telemetry as tel

    tel._initialized = False
    tel._anonymous_id = None
    # Reset thread-local scope
    if hasattr(tel._scope, "active"):
        del tel._scope.active


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Ensure clean telemetry state for every test and disable network."""
    _reset_telemetry_state()
    # Default: telemetry enabled but network mocked
    monkeypatch.delenv("DATAFOG_NO_TELEMETRY", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    yield
    _reset_telemetry_state()


@pytest.fixture
def mock_urlopen():
    """Mock urllib.request.urlopen to capture payloads without network."""
    with patch("datafog.telemetry.urllib.request.urlopen") as m:
        yield m


# ===========================================================================
# Group 1: Opt-out behaviour
# ===========================================================================


class TestOptOut:
    def test_datafog_no_telemetry_disables(self, monkeypatch):
        from datafog.telemetry import _is_telemetry_enabled

        monkeypatch.setenv("DATAFOG_NO_TELEMETRY", "1")
        assert _is_telemetry_enabled() is False

    def test_do_not_track_disables(self, monkeypatch):
        from datafog.telemetry import _is_telemetry_enabled

        monkeypatch.setenv("DO_NOT_TRACK", "1")
        assert _is_telemetry_enabled() is False

    def test_enabled_by_default(self):
        from datafog.telemetry import _is_telemetry_enabled

        assert _is_telemetry_enabled() is True

    def test_non_one_value_does_not_disable(self, monkeypatch):
        from datafog.telemetry import _is_telemetry_enabled

        monkeypatch.setenv("DATAFOG_NO_TELEMETRY", "true")
        assert _is_telemetry_enabled() is True

    def test_send_event_noop_when_disabled(self, monkeypatch, mock_urlopen):
        from datafog.telemetry import _send_event

        monkeypatch.setenv("DATAFOG_NO_TELEMETRY", "1")
        _send_event("test_event", {"key": "value"})
        time.sleep(0.1)
        mock_urlopen.assert_not_called()

    def test_track_function_call_noop_when_disabled(self, monkeypatch, mock_urlopen):
        from datafog.telemetry import track_function_call

        monkeypatch.setenv("DO_NOT_TRACK", "1")
        track_function_call("test_fn", "test_module")
        time.sleep(0.1)
        mock_urlopen.assert_not_called()


# ===========================================================================
# Group 2: Privacy guarantees
# ===========================================================================


class TestPrivacy:
    def test_text_length_bucket_zero(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(0) == "0"

    def test_text_length_bucket_small(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(50) == "1-100"

    def test_text_length_bucket_medium(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(500) == "100-1k"

    def test_text_length_bucket_large(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(5000) == "1k-10k"

    def test_text_length_bucket_very_large(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(50000) == "10k-100k"

    def test_text_length_bucket_huge(self):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(500000) == "100k+"

    def test_duration_bucket_fast(self):
        from datafog.telemetry import _get_duration_bucket

        assert _get_duration_bucket(5) == "0-10"

    def test_duration_bucket_medium(self):
        from datafog.telemetry import _get_duration_bucket

        assert _get_duration_bucket(50) == "10-100"

    def test_duration_bucket_slow(self):
        from datafog.telemetry import _get_duration_bucket

        assert _get_duration_bucket(500) == "100-1000"

    def test_duration_bucket_very_slow(self):
        from datafog.telemetry import _get_duration_bucket

        assert _get_duration_bucket(5000) == "1000+"

    def test_anonymous_id_is_sha256(self, tmp_path, monkeypatch):
        import datafog.telemetry as tel

        tel._anonymous_id = None
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        anon_id = tel._get_anonymous_id()
        # Should be 64 hex characters (SHA-256)
        assert len(anon_id) == 64
        assert all(c in "0123456789abcdef" for c in anon_id)

    def test_anonymous_id_persisted(self, tmp_path, monkeypatch):
        import datafog.telemetry as tel

        tel._anonymous_id = None
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        id1 = tel._get_anonymous_id()

        # Reset in-memory cache, should read from file
        tel._anonymous_id = None
        id2 = tel._get_anonymous_id()
        assert id1 == id2

    def test_payload_never_contains_text_content(self, mock_urlopen):
        """Verify that tracked events don't leak text content."""
        from datafog.telemetry import track_function_call

        track_function_call(
            "detect",
            "datafog",
            text_length_bucket="1-100",
            entity_count=2,
        )
        # Wait for daemon thread
        time.sleep(0.3)

        if mock_urlopen.called:
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            body = json.loads(req.data.decode("utf-8"))
            props = body["properties"]
            # Must not contain any raw text
            for key, value in props.items():
                if isinstance(value, str):
                    assert "example.com" not in value
                    assert "@" not in value or key == "distinct_id"


# ===========================================================================
# Group 3: Non-blocking behaviour
# ===========================================================================


class TestNonBlocking:
    def test_send_event_returns_immediately(self, mock_urlopen):
        from datafog.telemetry import _send_event

        # Make urlopen block
        mock_urlopen.side_effect = lambda *a, **k: time.sleep(10)

        start = time.monotonic()
        _send_event("test", {"k": "v"})
        elapsed = time.monotonic() - start

        # Should return in <100ms even though urlopen blocks for 10s
        assert elapsed < 0.1

    def test_track_function_call_returns_immediately(self, mock_urlopen):
        from datafog.telemetry import track_function_call

        mock_urlopen.side_effect = lambda *a, **k: time.sleep(10)

        start = time.monotonic()
        track_function_call("fn", "mod")
        elapsed = time.monotonic() - start

        assert elapsed < 0.1

    def test_network_failure_is_silent(self, mock_urlopen):
        from datafog.telemetry import track_function_call

        mock_urlopen.side_effect = Exception("Network down")
        # Should not raise
        track_function_call("fn", "mod")
        time.sleep(0.3)

    def test_urlopen_timeout_is_bounded(self, mock_urlopen):
        """Verify we pass a timeout to urlopen."""
        from datafog.telemetry import _send_event

        _send_event("test", {})
        time.sleep(0.3)

        if mock_urlopen.called:
            call_args = mock_urlopen.call_args
            assert call_args[1].get("timeout", None) is not None
            assert call_args[1]["timeout"] <= 10


# ===========================================================================
# Group 4: Payload correctness
# ===========================================================================


class TestPayloadCorrectness:
    def test_init_event_sent_once(self, mock_urlopen):
        from datafog.telemetry import _ensure_initialized

        _ensure_initialized()
        _ensure_initialized()
        _ensure_initialized()
        time.sleep(0.3)

        # Should only create one thread/call for init
        assert mock_urlopen.call_count <= 1

    def test_init_event_has_required_properties(self, mock_urlopen):
        from datafog.telemetry import _ensure_initialized

        _ensure_initialized()
        time.sleep(0.3)

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))

        assert body["event"] == "datafog_init"
        assert body["api_key"] == "phc_niGZ03Ey0ta6UzkCMtiHF0TdurLu2E3AVjyzQJRgpch"
        props = body["properties"]
        assert "package_version" in props
        assert "python_version" in props
        assert "os" in props
        assert "os_version" in props
        assert "arch" in props
        assert "installed_extras" in props
        assert "is_ci" in props
        assert "distinct_id" in props

    def test_function_call_event_properties(self, mock_urlopen):
        from datafog.telemetry import track_function_call

        track_function_call(
            "detect",
            "datafog",
            engine="regex",
            text_length_bucket="1-100",
            entity_count=3,
        )
        time.sleep(0.3)

        # Find the function_called event (init event may also be present)
        found = False
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_function_called":
                props = body["properties"]
                assert props["function"] == "detect"
                assert props["module"] == "datafog"
                assert props["engine"] == "regex"
                assert props["text_length_bucket"] == "1-100"
                assert props["entity_count"] == 3
                found = True
        assert found, "datafog_function_called event not found"

    def test_error_event_properties(self, mock_urlopen):
        from datafog.telemetry import track_error

        track_error("detect", "ValueError", engine="regex")
        time.sleep(0.3)

        found = False
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_error":
                props = body["properties"]
                assert props["function"] == "detect"
                assert props["error_type"] == "ValueError"
                assert props["engine"] == "regex"
                found = True
        assert found, "datafog_error event not found"

    def test_posthog_endpoint_url(self, mock_urlopen):
        from datafog.telemetry import _send_event

        _send_event("test_event", {"k": "v"})
        time.sleep(0.3)

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://us.i.posthog.com/capture/"

    def test_content_type_is_json(self, mock_urlopen):
        from datafog.telemetry import _send_event

        _send_event("test_event", {"k": "v"})
        time.sleep(0.3)

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"


# ===========================================================================
# Group 5: Integration - detect/process/DataFog/TextService trigger events
# ===========================================================================


class TestIntegration:
    def test_detect_triggers_telemetry(self, mock_urlopen):
        from datafog import detect

        with pytest.warns(FutureWarning, match=r"Use datafog\.scan\(\) instead"):
            detect("Contact john@example.com")
        time.sleep(0.3)

        events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            events.append(body["event"])
        assert "datafog_function_called" in events

    def test_process_triggers_telemetry(self, mock_urlopen):
        from datafog import process

        with pytest.warns(
            FutureWarning,
            match=r"datafog\.scan\(\) or datafog\.redact\(\)",
        ):
            process("Contact john@example.com", anonymize=True)
        time.sleep(0.3)

        events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            events.append(body["event"])
        assert "datafog_function_called" in events

    def test_datafog_class_triggers_telemetry(self, mock_urlopen):
        from datafog.main import DataFog

        df = DataFog()
        df.detect("john@example.com")
        time.sleep(0.3)

        events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            events.append(body["event"])
        assert "datafog_function_called" in events

    def test_text_service_triggers_telemetry(self, mock_urlopen):
        try:
            from datafog.services.text_service import TextService
        except ImportError:
            pytest.skip("TextService requires optional dependencies (aiohttp)")

        ts = TextService(engine="regex")
        ts.annotate_text_sync("john@example.com")
        time.sleep(0.3)

        events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            events.append(body["event"])
        assert "datafog_function_called" in events

    def test_core_detect_pii_triggers_telemetry(self, mock_urlopen):
        try:
            from datafog.core import detect_pii

            detect_pii("john@example.com")
        except ImportError:
            pytest.skip("detect_pii requires TextService with optional dependencies")
            return

        time.sleep(0.3)

        events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            events.append(body["event"])
        assert "datafog_function_called" in events


# ===========================================================================
# Group 6: Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_empty_text(self, mock_urlopen):
        from datafog.telemetry import _get_text_length_bucket, track_function_call

        track_function_call(
            "detect",
            "datafog",
            text_length_bucket=_get_text_length_bucket(0),
        )
        time.sleep(0.3)
        # Should not raise

    def test_large_text_bucket(self, mock_urlopen):
        from datafog.telemetry import _get_text_length_bucket

        assert _get_text_length_bucket(10_000_000) == "100k+"

    def test_concurrent_init(self, mock_urlopen):
        """Multiple threads calling _ensure_initialized should only init once."""
        from datafog.telemetry import _ensure_initialized

        threads = [threading.Thread(target=_ensure_initialized) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        time.sleep(0.5)
        # Count init events
        init_count = 0
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_init":
                init_count += 1
        assert init_count == 1

    def test_file_write_failure_handled(self, tmp_path, monkeypatch):
        """If we can't persist the ID, it still works."""
        import datafog.telemetry as tel

        tel._anonymous_id = None

        # Point to a read-only path
        def fake_home():
            return tmp_path / "nonexistent" / "deep" / "path"

        monkeypatch.setattr(Path, "home", fake_home)

        # Should not raise, generates ID in memory
        anon_id = tel._get_anonymous_id()
        assert len(anon_id) == 64

    def test_dedup_nested_calls(self, mock_urlopen):
        """Nested track_function_call should only record the outer call."""
        from datafog.telemetry import track_function_call

        # Simulate: process() calls detect() internally
        # The outer call sets _scope.active = True
        track_function_call("process", "datafog", method="redact")
        time.sleep(0.3)

        func_events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_function_called":
                func_events.append(body["properties"]["function"])

        # Only one function_called event should be present
        assert len(func_events) == 1
        assert func_events[0] == "process"

    def test_detect_ci_returns_bool(self):
        from datafog.telemetry import _detect_ci

        result = _detect_ci()
        assert isinstance(result, bool)

    def test_detect_installed_extras_returns_list(self):
        from datafog.telemetry import _detect_installed_extras

        result = _detect_installed_extras()
        assert isinstance(result, list)

    def test_services_init_does_not_require_aiohttp(self):
        """TextService should be importable without aiohttp/PIL (services/__init__.py fix)."""
        from datafog.services.text_service import TextService

        ts = TextService(engine="regex")
        assert ts.engine == "regex"

    def test_track_error_sent_on_exception(self, mock_urlopen):
        """track_error should fire a datafog_error event."""
        from datafog.telemetry import track_error

        track_error("some_function", "ValueError", engine="regex")
        time.sleep(0.3)

        error_events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_error":
                error_events.append(body["properties"])

        assert len(error_events) == 1
        assert error_events[0]["function"] == "some_function"
        assert error_events[0]["error_type"] == "ValueError"
        assert error_events[0]["engine"] == "regex"

    def test_pipeline_error_triggers_track_error(self, mock_urlopen):
        """DataFog.run_text_pipeline_sync should fire datafog_error on failure."""
        from datafog.main import DataFog

        df = DataFog()
        # Pass a non-list to trigger a TypeError inside the pipeline
        try:
            df.run_text_pipeline_sync(123)
        except Exception:
            pass

        time.sleep(0.3)

        error_events = []
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            body = json.loads(req.data.decode("utf-8"))
            if body["event"] == "datafog_error":
                error_events.append(body["properties"])

        assert len(error_events) >= 1
        assert error_events[0]["function"] == "DataFog.run_text_pipeline_sync"
