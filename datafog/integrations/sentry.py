"""Sentry SDK integration: scrub PII from events before they leave the process.

Usage::

    import sentry_sdk
    from datafog.integrations.sentry import DataFogSentryIntegration

    sentry_sdk.init(
        dsn="...",
        integrations=[DataFogSentryIntegration()],
    )

Or wire the scrubber into ``before_send`` directly::

    sentry_sdk.init(dsn="...", before_send=scrub_event)

Behavior:

- The integration registers a *global event processor*, so it scrubs both
  error events and transactions (span descriptions and data ride inside
  transaction events) while leaving the single ``before_send`` slot free
  for the application's own callback.
- Scrubbing is content-based: every string value in the event — messages,
  exception values, stack-frame local variables, breadcrumbs, request
  data, ``extra``, tags, span descriptions — is scanned and findings are
  replaced with ``[TYPE_N]`` tokens. This catches PII that Sentry's
  built-in ``EventScrubber`` misses, because that scrubber only matches
  sensitive *key names* and never inspects values.
- ``fail_policy`` — ``open`` (default) sends the event unscrubbed if the
  engine errors, so a scrubber bug never costs you crash reports;
  ``closed`` drops the event instead, for compliance deployments where
  unscanned egress is worse than a missing event.

Errors report entity type counts only — matched PII is never echoed into
logs or exceptions.

Requires ``sentry-sdk`` >= 2.0 (this module is not imported by ``datafog``
core; install with ``pip install datafog[sentry]`` or alongside your app's
existing sentry-sdk).
"""

import logging
from typing import Any, Optional

import sentry_sdk
from sentry_sdk.integrations import Integration

# High-precision defaults, matching the LiteLLM guardrail and Claude Code
# hook adapters: noisy-in-practice types (IP_ADDRESS, DOB, ZIP) must be
# opted into explicitly.
DEFAULT_ENTITY_TYPES = ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"]

VALID_FAIL_POLICIES = {"open", "closed"}

# Per-string and per-event scan caps, mirroring the Claude Code hook: a
# pathological payload (huge repr in a frame var, giant request body) must
# not stall event delivery. Text beyond a cap is REPLACED with an
# [UNSCANNED_N_CHARS] marker, never sent raw: emitting an unscanned tail
# would let a PII value that straddles the cut point reassemble unredacted,
# and unscanned egress is the one thing this integration must not do. Both
# caps sit far above Sentry's own event-size limits, so real events never
# reach them.
MAX_SCAN_CHARS = 1_000_000
TOTAL_SCAN_CHARS = 8_000_000

# Top-level event fields that are machine identifiers, not free text.
# Skipping them avoids mangling values that only *look* like PII (a release
# tag containing an @, a server hostname) and matches what Sentry's own
# EventScrubber leaves alone. The skip applies at the event's top level
# only — a nested key that happens to be named "release" (e.g. inside
# ``extra``) is still scanned.
_SKIP_TOP_LEVEL_KEYS = frozenset(
    {
        "event_id",
        "timestamp",
        "start_timestamp",
        "received",
        "platform",
        "sdk",
        "modules",
        "release",
        "dist",
        "environment",
        "server_name",
        "type",
        "level",
    }
)

logger = logging.getLogger(__name__)


class _EventScrubber:
    """Single-event scrub pass: walks the event, redacts string values.

    Mutates containers in place — deliberate: the Sentry processor contract
    is mutate-and-return, and deep-copying every event would double memory
    while leaving an unredacted copy other processors could still see.

    A fresh instance is created per event (see ``_scrub_with_policy``), so
    ``counts``, ``_budget``, and ``_seen`` are never shared across events or
    threads. Do not hoist construction out of the per-event path: a reused
    instance would leak budget and alias state between events.
    """

    def __init__(
        self,
        entity_types: list[str],
        allowlist: Optional[list[str]],
        allowlist_patterns: Optional[list[str]],
    ) -> None:
        self.entity_types = entity_types
        self.allowlist = allowlist
        self.allowlist_patterns = allowlist_patterns
        self.counts: dict[str, int] = {}
        self.unscanned_chars = 0
        self._budget = TOTAL_SCAN_CHARS
        self._seen: set[int] = set()

    def _unscanned(self, length: int) -> str:
        self.unscanned_chars += length
        return f"[UNSCANNED_{length}_CHARS]"

    def _redact_string(self, text: str) -> str:
        limit = min(MAX_SCAN_CHARS, self._budget)
        if limit <= 0:
            return self._unscanned(len(text))
        import datafog

        chunk = text[:limit]
        self._budget -= len(chunk)
        result = datafog.redact(
            chunk,
            engine="regex",
            entity_types=self.entity_types,
            allowlist=self.allowlist,
            allowlist_patterns=self.allowlist_patterns,
        )
        for entity in result.entities:
            self.counts[entity.type] = self.counts.get(entity.type, 0) + 1
        tail = text[len(chunk) :]
        if tail:
            # Never reattach the unscanned tail raw: a PII value straddling
            # the cut point would fail to match in the truncated chunk and
            # reassemble unredacted in the output.
            return result.redacted_text + self._unscanned(len(tail))
        return result.redacted_text if result.entities else text

    def _transform(self, value: Any, stack: list[Any]) -> Any:
        """Redact a string, or queue a container for walking.

        Tuples and sets are rebuilt as lists — the Sentry serializer emits
        all three as JSON arrays, and a list can be walked and mutated in
        place. ``_seen`` dedupes aliased containers, so a structure reachable
        from two places is scanned once (double-scanning would double-spend
        the budget) and cyclic structures terminate. Other value types
        (numbers, custom objects) pass through untouched: the SDK reprs
        custom objects only after processors run, so their contents are
        out of reach here.
        """
        if isinstance(value, str):
            return self._redact_string(value)
        if isinstance(value, (tuple, set, frozenset)):
            value = list(value)
        if isinstance(value, (dict, list)) and id(value) not in self._seen:
            self._seen.add(id(value))
            stack.append(value)
        return value

    def scrub(self, event: dict) -> dict:
        """Redact every string value in the event.

        Iterative (explicit stack), so adversarially deep structures in
        ``extra`` or frame vars cannot trigger ``RecursionError`` and
        silently skip the scan. Dict *keys* are left alone, matching
        Sentry's EventScrubber.
        """
        stack: list[Any] = []
        for key in list(event.keys()):
            if key in _SKIP_TOP_LEVEL_KEYS:
                continue
            new_value = self._transform(event[key], stack)
            if new_value is not event[key]:
                event[key] = new_value
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key in list(current.keys()):
                    new_value = self._transform(current[key], stack)
                    if new_value is not current[key]:
                        current[key] = new_value
            else:  # list — _transform only queues dicts and lists
                for index, value in enumerate(current):
                    new_value = self._transform(value, stack)
                    if new_value is not value:
                        current[index] = new_value
        if self.unscanned_chars:
            logger.debug(
                "DataFog Sentry scrubber: %d chars beyond scan caps replaced "
                "with [UNSCANNED_N_CHARS] markers",
                self.unscanned_chars,
            )
        return event


def _summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{etype} x{n}" for etype, n in sorted(counts.items()))


def _scrub_with_policy(
    event: dict,
    entity_types: list[str],
    allowlist: Optional[list[str]],
    allowlist_patterns: Optional[list[str]],
    fail_policy: str,
) -> Optional[dict]:
    scrubber = _EventScrubber(entity_types, allowlist, allowlist_patterns)
    try:
        scrubbed = scrubber.scrub(event)
    except Exception as exc:  # noqa: BLE001 — fail policy decides
        # Only the exception *type* is ever logged. Engine exception
        # messages can embed the text being scanned, so interpolating
        # str(exc) would leak the PII this integration exists to contain.
        if fail_policy == "closed":
            logger.warning(
                "DataFog Sentry scrubber failed and fail_policy is 'closed'; "
                "dropping event (%s).",
                type(exc).__name__,
            )
            return None
        logger.warning(
            "DataFog Sentry scrubber error (fail-open, event sent unscanned "
            "beyond partial redaction): %s",
            type(exc).__name__,
        )
        return event
    if scrubber.counts:
        logger.debug("DataFog Sentry scrubber redacted: %s", _summary(scrubber.counts))
    return scrubbed


def scrub_event(
    event: dict,
    hint: Optional[dict] = None,
    *,
    entity_types: Optional[list[str]] = None,
    allowlist: Optional[list[str]] = None,
    allowlist_patterns: Optional[list[str]] = None,
    fail_policy: str = "open",
) -> Optional[dict]:
    """Scrub a Sentry event dict; drop-in ``before_send`` callback.

    The two positional parameters match Sentry's ``before_send(event, hint)``
    signature so the function can be passed directly. The keyword-only
    options mirror :class:`DataFogSentryIntegration`; to preconfigure them,
    wrap in ``functools.partial`` or use the integration instead.
    """
    if fail_policy not in VALID_FAIL_POLICIES:
        raise ValueError(f"fail_policy must be one of: {sorted(VALID_FAIL_POLICIES)}")
    return _scrub_with_policy(
        event,
        entity_types or DEFAULT_ENTITY_TYPES,
        allowlist,
        allowlist_patterns,
        fail_policy,
    )


class DataFogSentryIntegration(Integration):
    """Content-based PII scrubbing for the Sentry Python SDK."""

    identifier = "datafog"

    def __init__(
        self,
        entity_types: Optional[list[str]] = None,
        allowlist: Optional[list[str]] = None,
        allowlist_patterns: Optional[list[str]] = None,
        fail_policy: str = "open",
    ) -> None:
        if fail_policy not in VALID_FAIL_POLICIES:
            raise ValueError(
                f"fail_policy must be one of: {sorted(VALID_FAIL_POLICIES)}"
            )
        self.entity_types = entity_types or DEFAULT_ENTITY_TYPES
        self.allowlist = allowlist
        self.allowlist_patterns = allowlist_patterns
        self.fail_policy = fail_policy

    @staticmethod
    def setup_once() -> None:
        # Registered once per process. The processor resolves the integration
        # instance from the *current* client on every event, so config always
        # comes from the active ``sentry_sdk.init`` call and clients without
        # this integration are passed through untouched.
        from sentry_sdk.scope import add_global_event_processor

        add_global_event_processor(_global_processor)


def _global_processor(event: dict, hint: Optional[dict]) -> Optional[dict]:
    try:
        integration = sentry_sdk.get_client().get_integration(DataFogSentryIntegration)
    except Exception as exc:  # noqa: BLE001 — never break event delivery
        # The lookup runs outside _scrub_with_policy's error handling and no
        # integration (hence no fail_policy) is resolvable here, so the only
        # safe default is to pass the event through.
        logger.warning(
            "DataFog Sentry integration lookup failed (event passed "
            "through unscanned): %s",
            type(exc).__name__,
        )
        return event
    if integration is None:
        return event
    return _scrub_with_policy(
        event,
        integration.entity_types,
        integration.allowlist,
        integration.allowlist_patterns,
        integration.fail_policy,
    )
