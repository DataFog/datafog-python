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

Requires ``litellm`` (this module is not imported by ``datafog`` core).
"""

import logging
from typing import Any, Optional

from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

# High-precision defaults, matching the Claude Code hook adapter: noisy-in-
# practice types (IP_ADDRESS, DOB, ZIP) must be opted into explicitly.
DEFAULT_ENTITY_TYPES = ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"]

VALID_ACTIONS = {"redact", "block"}
VALID_FAIL_POLICIES = {"open", "closed"}

logger = logging.getLogger(__name__)


def _redact_text(text: str, entity_types: list[str]) -> tuple[str, dict[str, int]]:
    """Redact ``text``; return (redacted_text, counts per entity type)."""
    import datafog

    result = datafog.redact(text, engine="regex", entity_types=entity_types)
    counts: dict[str, int] = {}
    for entity in result.entities:
        counts[entity.type] = counts.get(entity.type, 0) + 1
    return result.redacted_text, counts


def _summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{etype} x{n}" for etype, n in sorted(counts.items()))


class DataFogGuardrail(CustomGuardrail):
    """Offline PII guardrail for the LiteLLM proxy, powered by datafog."""

    def __init__(
        self,
        action: str = "redact",
        entity_types: Optional[list[str]] = None,
        fail_policy: str = "open",
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
        super().__init__(**kwargs)

    def _process_content(self, content: Any) -> tuple[Any, dict[str, int]]:
        """Redact a message content value (str or list of content parts)."""
        counts: dict[str, int] = {}
        if isinstance(content, str):
            redacted, counts = _redact_text(content, self.entity_types)
            return redacted, counts
        if isinstance(content, list):
            new_parts = []
            skipped_parts = 0
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    redacted, part_counts = _redact_text(
                        part["text"], self.entity_types
                    )
                    new_parts.append({**part, "text": redacted})
                    for etype, n in part_counts.items():
                        counts[etype] = counts.get(etype, 0) + n
                else:
                    # Images and other non-text parts are not scanned —
                    # count them so the blind spot is auditable.
                    new_parts.append(part)
                    skipped_parts += 1
            if skipped_parts:
                logger.debug(
                    "DataFog guardrail: %d non-text content parts not scanned",
                    skipped_parts,
                )
            return new_parts, counts
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
        messages = data.get("messages")
        if not isinstance(messages, list):
            return data

        total_counts: dict[str, int] = {}
        new_messages = []
        try:
            for message in messages:
                if isinstance(message, dict) and "content" in message:
                    new_content, counts = self._process_content(message["content"])
                    new_messages.append({**message, "content": new_content})
                    for etype, n in counts.items():
                        total_counts[etype] = total_counts.get(etype, 0) + n
                else:
                    new_messages.append(message)
        except Exception as exc:  # noqa: BLE001 — fail policy decides
            self._handle_engine_error(exc)
            return data

        if not total_counts:
            return data

        self._record_guardrail_logging(data, total_counts)

        if self.action == "block":
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

        return {**data, "messages": new_messages}

    def _record_guardrail_logging(
        self, data: dict, total_counts: dict[str, int]
    ) -> None:
        """Record the decision into litellm's standard guardrail logging."""
        try:
            self.add_standard_logging_guardrail_information_to_request_data(
                guardrail_json_response=_summary(total_counts),
                request_data=data,
                guardrail_status=(
                    "guardrail_intervened" if self.action == "block" else "success"
                ),
                masked_entity_count=dict(total_counts),
            )
        except Exception:  # noqa: BLE001 — observability must never break traffic
            logger.debug("could not record guardrail logging information")

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        """Redact PII from model responses.

        Mutates ``response`` in place — deliberate: litellm post_call
        guardrails share the response object rather than cloning it, and
        an unredacted clone escaping through another callback would defeat
        the purpose.
        """
        choices = getattr(response, "choices", None)
        if not choices:
            return response
        try:
            skipped_parts = 0
            for choice in choices:
                message = getattr(choice, "message", None)
                if message is not None and isinstance(message.content, str):
                    redacted, counts = _redact_text(message.content, self.entity_types)
                    if counts:
                        message.content = redacted
                elif message is not None and message.content is not None:
                    skipped_parts += 1
            if skipped_parts:
                logger.debug(
                    "DataFog guardrail: %d non-text response parts not scanned",
                    skipped_parts,
                )
        except Exception as exc:  # noqa: BLE001 — fail policy decides
            self._handle_engine_error(exc)
        return response
