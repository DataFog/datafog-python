"""LiteLLM guardrail adapter: redact or block PII at the gateway.

Usage (LiteLLM proxy ``config.yaml``)::

    guardrails:
      - guardrail_name: "datafog-pii"
        litellm_params:
          guardrail: datafog.integrations.litellm_guardrail.DataFogGuardrail
          mode: "pre_call"
          action: "redact"          # or "block"
          fail_policy: "open"       # or "closed"
          # entity_types: ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"]

Behavior:

- ``pre_call``  — scans request messages. ``redact`` (default) replaces
  findings with ``[TYPE_N]`` tokens before the request leaves the gateway;
  ``block`` rejects the request outright.
- ``post_call`` — redacts findings from model responses before they reach
  the client.
- ``fail_policy`` — ``open`` (default) lets traffic through unscanned if
  the engine errors, so a guardrail bug never takes down the gateway;
  ``closed`` rejects traffic instead, for compliance deployments where
  unscanned egress is worse than downtime.

Errors and block messages report entity type counts only — matched PII is
never echoed into logs, exceptions, or proxy responses.

Requires ``litellm`` and ``fastapi`` (this module is not imported by
``datafog`` core; the LiteLLM proxy, where this runs, always ships fastapi).
"""

import copy
import logging
import re
from typing import Any, Optional

from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

# High-precision defaults, matching the Claude Code hook adapter: noisy-in-
# practice types (IP_ADDRESS, DOB, ZIP) must be opted into explicitly.
DEFAULT_ENTITY_TYPES = ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"]

VALID_ACTIONS = {"redact", "block"}
VALID_FAIL_POLICIES = {"open", "closed"}
MAX_STREAM_CHARS = 8_000_000
MAX_STREAM_CHUNKS = 100_000

logger = logging.getLogger(__name__)


class _RedactionSession:
    """Token assignments belong to one request or response, never the adapter."""

    def __init__(self, strings=()):
        self.tokens: dict[tuple[str, str], str] = {}
        self.counters: dict[str, int] = {}
        self.reserved = {
            token for text in strings for token in re.findall(r"\[[A-Z_]+_\d+\]", text)
        }

    def token(self, entity):
        key = (entity.type, entity.text)
        if key not in self.tokens:
            number = self.counters.get(entity.type, 0) + 1
            while f"[{entity.type}_{number}]" in self.reserved:
                number += 1
            token = f"[{entity.type}_{number}]"
            self.counters[entity.type] = number
            self.tokens[key] = token
            self.reserved.add(token)
        return self.tokens[key]


def _strings(value):
    stack = [value]
    visited = set()
    while stack:
        item = stack.pop()
        if isinstance(item, (dict, list)):
            if id(item) in visited:
                continue
            visited.add(id(item))
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            stack.extend(item.values())
            stack.extend(item.keys())
        elif isinstance(item, list):
            stack.extend(item)


def _get(value, name, default=None):
    return (
        value.get(name, default)
        if isinstance(value, dict)
        else getattr(value, name, default)
    )


def _set(value, name, item):
    if isinstance(value, dict):
        value[name] = item
    else:
        setattr(value, name, item)


def _redact_text(
    text: str,
    entity_types: list[str],
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
    session: _RedactionSession | None = None,
) -> tuple[str, dict[str, int]]:
    """Redact ``text``; return (redacted_text, counts per entity type)."""
    import datafog

    result = datafog.redact(
        text,
        engine="regex",
        entity_types=entity_types,
        allowlist=allowlist,
        allowlist_patterns=allowlist_patterns,
    )
    counts: dict[str, int] = {}
    for entity in result.entities:
        counts[entity.type] = counts.get(entity.type, 0) + 1
    session = session or _RedactionSession([text])
    parts = []
    cursor = 0
    for entity in sorted(result.entities, key=lambda entity: entity.start):
        parts.extend((text[cursor : entity.start], session.token(entity)))
        cursor = entity.end
    parts.append(text[cursor:])
    return "".join(parts), counts


def _summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{etype} x{n}" for etype, n in sorted(counts.items()))


class DataFogGuardrail(CustomGuardrail):
    """Offline PII guardrail for the LiteLLM proxy, powered by datafog."""

    def __init__(
        self,
        action: str = "redact",
        entity_types: Optional[list[str]] = None,
        fail_policy: str = "open",
        allowlist: Optional[list[str]] = None,
        allowlist_patterns: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        if action not in VALID_ACTIONS:
            raise ValueError(f"action must be one of: {sorted(VALID_ACTIONS)}")
        if fail_policy not in VALID_FAIL_POLICIES:
            raise ValueError(
                f"fail_policy must be one of: {sorted(VALID_FAIL_POLICIES)}"
            )
        self.action = action
        self.entity_types = entity_types or DEFAULT_ENTITY_TYPES
        self.fail_policy = fail_policy
        self.allowlist = allowlist
        self.allowlist_patterns = allowlist_patterns
        super().__init__(**kwargs)

    def _process_content(
        self, content: Any, session=None
    ) -> tuple[Any, dict[str, int]]:
        """Walk textual input, including nested tool arguments and content parts."""
        session = session or _RedactionSession(_strings(content))
        counts: dict[str, int] = {}
        if isinstance(content, str):
            redacted, counts = _redact_text(
                content,
                self.entity_types,
                self.allowlist,
                self.allowlist_patterns,
                session,
            )
            return redacted, counts
        if isinstance(content, (list, dict)):
            items = enumerate(content) if isinstance(content, list) else content.items()
            output = [] if isinstance(content, list) else {}
            for key, value in items:
                # Media payloads are opaque; preserve them while scanning any
                # textual sibling. name/id/url in ordinary user data are text.
                media_type = content.get("type") if isinstance(content, dict) else None
                if not isinstance(media_type, str):
                    media_type = None
                opaque = {
                    "image_url": {"image_url"},
                    "input_image": {"image_url", "file_id"},
                    "image": {"source"},
                    "input_audio": {"input_audio"},
                    "audio": {"source", "data"},
                    "video_url": {"video_url"},
                    "file": {"file"},
                    "input_file": {"file_id", "file_data"},
                }
                if key in opaque.get(media_type, set()):
                    new_value, found = value, {}
                else:
                    new_value, found = self._process_content(value, session)
                if isinstance(output, list):
                    output.append(new_value)
                else:
                    output[key] = new_value
                for label, count in found.items():
                    counts[label] = counts.get(label, 0) + count
            return output, counts
        return content, counts

    def _handle_engine_error(self, exc: Exception) -> None:
        # Only the exception *type* is ever logged or re-raised. Engine
        # exception messages can embed the text being scanned, so chaining
        # (`from exc`) or interpolating str(exc) would leak matched PII into
        # tracebacks and logs — the exact thing this guardrail exists to
        # prevent. `from None` suppresses both __cause__ and __context__.
        if self.fail_policy == "closed":
            # RuntimeError (no status_code attr) intentionally surfaces as
            # HTTP 500: an engine failure is a server fault, distinct from
            # the policy block below, which is a 400.
            raise RuntimeError(
                "DataFog guardrail failed and fail_policy is 'closed'; "
                f"rejecting unscanned traffic ({type(exc).__name__})."
            ) from None
        logger.warning(
            "DataFog guardrail error (fail-open, traffic unscanned): %s",
            type(exc).__name__,
        )

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> dict:
        total_counts: dict[str, int] = {}
        new_data = dict(data)
        fields = ("messages", "prompt", "input")
        session = _RedactionSession(
            text for field in fields for text in _strings(data.get(field))
        )
        try:
            for field in fields:
                if field in data:
                    new_data[field], counts = self._process_content(
                        data[field], session
                    )
                    for label, count in counts.items():
                        total_counts[label] = total_counts.get(label, 0) + count
        except Exception as exc:  # noqa: BLE001 — fail policy decides
            self._handle_engine_error(exc)
            return data

        if not total_counts:
            return data

        if self.action == "block":
            self._record_guardrail_logging(data, total_counts)
            # HTTPException(400) is one of the exception types litellm's
            # _is_guardrail_intervention recognizes, so the block is
            # classified as a policy intervention (not a backend failure)
            # and reaches the client as a 400, not a 500.
            # Counts only — never the matched values.
            raise HTTPException(
                status_code=400,
                detail={
                    "error": (
                        f"DataFog PII guardrail: request blocked, messages "
                        f"contain {_summary(total_counts)}."
                    )
                },
            )

        self._record_guardrail_logging(new_data, total_counts)
        return new_data

    def _record_guardrail_logging(
        self, data: dict, total_counts: dict[str, int]
    ) -> None:
        """Record the decision into litellm's standard guardrail logging."""
        try:
            self.add_standard_logging_guardrail_information_to_request_data(
                guardrail_json_response=_summary(total_counts),
                request_data=data,
                guardrail_status="guardrail_intervened",
                masked_entity_count=dict(total_counts),
            )
        except Exception:  # noqa: BLE001 — observability must never break traffic
            logger.debug("could not record guardrail logging information")

    @staticmethod
    def _response_fields(response):
        """Yield only generated text fields, preserving response metadata."""
        for choice in _get(response, "choices", []) or []:
            if isinstance(_get(choice, "text"), str):
                yield choice, "text"
            message = _get(choice, "message")
            if message is None:
                continue
            yield message, "content"
            for call in _get(message, "tool_calls", []) or []:
                function = _get(call, "function")
                if function is not None:
                    yield function, "arguments"
            function = _get(message, "function_call")
            if function is not None:
                yield function, "arguments"

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        """Redact generated text in place after every field has been scanned."""
        try:
            fields = list(self._response_fields(response))
            session = _RedactionSession(
                text
                for target, field in fields
                for text in _strings(_get(target, field))
            )
            changes = []
            for target, field in fields:
                value, _ = self._process_content(_get(target, field), session)
                changes.append((target, field, value))
            for target, field, value in changes:
                _set(target, field, value)
        except Exception as exc:  # noqa: BLE001 — fail policy decides
            self._handle_engine_error(exc)
        return response

    async def async_post_call_streaming_iterator_hook(
        self, user_api_key_dict, response, request_data
    ):
        """Buffer to completion before emitting, protecting split entities.

        Native text and tool argument deltas are joined per choice/tool. The
        first corresponding delta carries the redacted text and later deltas
        are empty; metadata and finish events retain their original order.
        Incomplete or oversized streams are rejected without emitting chunks.
        """
        chunks = []
        groups = {}
        size = 0
        try:
            async for original in response:
                # Iterators may reuse a mutable chunk object. Keep each emitted
                # delta's value and metadata as they existed when received.
                chunk = copy.deepcopy(original)
                chunks.append(chunk)
                for position, choice in enumerate(_get(chunk, "choices", []) or []):
                    index = _get(choice, "index", position)
                    fields = [((index, "text"), choice, "text")]
                    delta = _get(choice, "delta")
                    if delta is not None:
                        fields.append(((index, "content"), delta, "content"))
                        for call_position, call in enumerate(
                            _get(delta, "tool_calls", []) or []
                        ):
                            function = _get(call, "function")
                            if function is not None:
                                fields.append(
                                    (
                                        (
                                            index,
                                            "tool",
                                            _get(call, "index", call_position),
                                        ),
                                        function,
                                        "arguments",
                                    )
                                )
                        function = _get(delta, "function_call")
                        if function is not None:
                            fields.append(
                                ((index, "function_call"), function, "arguments")
                            )
                    for key, target, field in fields:
                        value = _get(target, field)
                        if isinstance(value, str):
                            size += len(value)
                            groups.setdefault(key, []).append((target, field, value))
                if size > MAX_STREAM_CHARS or len(chunks) > MAX_STREAM_CHUNKS:
                    raise _StreamLimitExceeded()
        except _StreamLimitExceeded:
            raise RuntimeError(
                "DataFog streaming response exceeded the scan budget; rejecting unscanned output"
            ) from None
        except Exception as exc:
            # A failed upstream stream cannot be safely completed or replayed.
            # Provider exceptions can contain private prompt/response text.
            raise RuntimeError(
                f"DataFog streaming response did not complete ({type(exc).__name__}); rejecting incomplete output"
            ) from None
        try:
            texts = [
                "".join(value for _, _, value in group) for group in groups.values()
            ]
            session = _RedactionSession(texts)
            changes = []
            for group, text in zip(groups.values(), texts, strict=True):
                redacted, _ = self._process_content(text, session)
                changes.extend(
                    (target, field, redacted if i == 0 else "")
                    for i, (target, field, _) in enumerate(group)
                )
            for target, field, value in changes:
                _set(target, field, value)
        except Exception as exc:
            self._handle_engine_error(exc)
        for chunk in chunks:
            yield chunk


class _StreamLimitExceeded(Exception):
    """Internal marker; stream-budget failures always reject output."""
