"""
Anonymous, opt-in usage telemetry for DataFog.

Collects anonymous usage data to help the DataFog team understand which engines,
functions, and features are actually used. No text content is ever sent.

Telemetry is disabled by default. Opt in by setting:
    DATAFOG_TELEMETRY=1

Force telemetry off by setting either environment variable:
    DATAFOG_NO_TELEMETRY=1
    DO_NOT_TRACK=1
"""

import hashlib
import json
import os
import platform
import threading
import time
import urllib.request
from pathlib import Path

_POSTHOG_API_KEY = "phc_niGZ03Ey0ta6UzkCMtiHF0TdurLu2E3AVjyzQJRgpch"
_POSTHOG_HOST = "https://us.i.posthog.com"

_initialized = False
_init_lock = threading.Lock()
_anonymous_id = None

# Thread-local scope for deduplication across nested calls
_scope = threading.local()


def _env_truthy(name: str) -> bool:
    """Return True when an environment variable explicitly opts in/out."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled (opt-in, with opt-out overrides)."""
    if _env_truthy("DATAFOG_NO_TELEMETRY"):
        return False
    if _env_truthy("DO_NOT_TRACK"):
        return False
    return _env_truthy("DATAFOG_TELEMETRY")


def _get_anonymous_id() -> str:
    """Get or create a deterministic anonymous ID based on machine info.

    The ID is a SHA-256 hash of machine-specific information, persisted
    to ~/.datafog/.telemetry_id for consistency across sessions.
    No PII is stored or transmitted.
    """
    global _anonymous_id
    if _anonymous_id is not None:
        return _anonymous_id

    telemetry_dir = Path.home() / ".datafog"
    telemetry_file = telemetry_dir / ".telemetry_id"

    # Try to read persisted ID
    try:
        if telemetry_file.exists():
            stored_id = telemetry_file.read_text().strip()
            if stored_id:
                _anonymous_id = stored_id
                return _anonymous_id
    except Exception:
        pass

    # Generate deterministic ID from machine info
    machine_info = f"{platform.node()}-{platform.machine()}-{os.getuid() if hasattr(os, 'getuid') else 'nouid'}"
    _anonymous_id = hashlib.sha256(machine_info.encode()).hexdigest()

    # Persist to disk
    try:
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        telemetry_file.write_text(_anonymous_id)
    except Exception:
        pass

    return _anonymous_id


def _get_text_length_bucket(length: int) -> str:
    """Convert exact text length to a privacy-safe bucket."""
    if length == 0:
        return "0"
    elif length <= 100:
        return "1-100"
    elif length <= 1000:
        return "100-1k"
    elif length <= 10000:
        return "1k-10k"
    elif length <= 100000:
        return "10k-100k"
    else:
        return "100k+"


def _get_duration_bucket(duration_ms: float) -> str:
    """Convert exact duration to a coarse bucket."""
    if duration_ms <= 10:
        return "0-10"
    elif duration_ms <= 100:
        return "10-100"
    elif duration_ms <= 1000:
        return "100-1000"
    else:
        return "1000+"


def _detect_installed_extras() -> list:
    """Probe which optional extras are installed."""
    extras = []

    try:
        import spacy  # noqa: F401

        extras.append("nlp")
    except ImportError:
        pass

    try:
        import gliner  # noqa: F401

        extras.append("nlp-advanced")
    except ImportError:
        pass

    try:
        import pytesseract  # noqa: F401

        extras.append("ocr")
    except ImportError:
        pass

    try:
        import typer  # noqa: F401

        extras.append("cli")
    except ImportError:
        pass

    try:
        import pyspark  # noqa: F401

        extras.append("distributed")
    except ImportError:
        pass

    return extras


def _detect_ci() -> bool:
    """Check if running in a CI environment."""
    ci_vars = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CIRCLECI",
        "TRAVIS",
        "JENKINS_URL",
        "BUILDKITE",
        "TF_BUILD",
        "CODEBUILD_BUILD_ID",
    ]
    return any(os.environ.get(v) for v in ci_vars)


def _send_event(event_name: str, properties: dict) -> None:
    """POST event to PostHog /capture/ endpoint in a daemon thread.

    Fire-and-forget: failures are silently ignored.
    """
    if not _is_telemetry_enabled():
        return

    def _post():
        try:
            payload = json.dumps(
                {
                    "api_key": _POSTHOG_API_KEY,
                    "event": event_name,
                    "properties": {
                        "distinct_id": _get_anonymous_id(),
                        **properties,
                    },
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                f"{_POSTHOG_HOST}/capture/",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    t = threading.Thread(target=_post, daemon=True)
    t.start()


def _ensure_initialized() -> None:
    """Send datafog_init event once per process, thread-safe."""
    global _initialized
    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return
        _initialized = True

    if not _is_telemetry_enabled():
        return

    try:
        from .__about__ import __version__
    except Exception:
        __version__ = "unknown"

    uname = platform.uname()
    _send_event(
        "datafog_init",
        {
            "package_version": __version__,
            "python_version": platform.python_version(),
            "os": uname.system,
            "os_version": uname.release,
            "arch": uname.machine,
            "installed_extras": _detect_installed_extras(),
            "is_ci": _detect_ci(),
        },
    )


def track_function_call(function_name: str, module: str, **kwargs) -> None:
    """Track a public API function call.

    Uses thread-local scope to deduplicate nested calls (e.g., process()
    calling detect()). Only the outermost call is tracked.
    """
    if not _is_telemetry_enabled():
        return

    # Deduplication: skip if already inside a tracked scope
    if getattr(_scope, "active", False):
        return

    _scope.active = True
    try:
        _ensure_initialized()
        properties = {
            "function": function_name,
            "module": module,
        }
        properties.update(kwargs)
        _send_event("datafog_function_called", properties)
    finally:
        _scope.active = False


def track_error(function_name: str, error_type: str, **kwargs) -> None:
    """Track an error in a public API function.

    Only sends the error class name, never the message (could contain PII).
    """
    if not _is_telemetry_enabled():
        return

    _ensure_initialized()
    properties = {
        "function": function_name,
        "error_type": error_type,
    }
    properties.update(kwargs)
    _send_event("datafog_error", properties)
