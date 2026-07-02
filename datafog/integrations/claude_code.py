"""Claude Code hook adapter: an offline PII firewall for agent tool calls.

Speaks the Claude Code hooks protocol (JSON on stdin, JSON on stdout):

- ``PreToolUse``   — gate outbound tool calls (Bash, WebFetch, Write, MCP
  tools). PII in the tool input yields an ``ask`` (default) or ``deny``
  permission decision, so data is stopped *before* it leaves the machine.
- ``UserPromptSubmit`` — non-blocking: warns the model that the prompt
  contains PII so it avoids repeating it in output or logs.
- ``PostToolUse``  — non-blocking: warns when a tool result carries PII
  into the conversation context.

Configuration (environment variables):

- ``DATAFOG_HOOK_ACTION``: ``ask`` (default) or ``deny`` for PreToolUse.
- ``DATAFOG_HOOK_ENTITIES``: comma-separated entity types to detect.
  Defaults to the high-precision set; noisy-in-code types (IP_ADDRESS,
  DOB, ZIP) must be opted into.
- ``DATAFOG_HOOK_ALLOWLIST``: comma-separated exact values to exempt
  (your own support address, documentation placeholders).
- ``DATAFOG_HOOK_ALLOWLIST_PATTERNS``: comma-separated regexes; findings
  whose full text matches are exempt (note: a pattern containing a comma
  cannot be expressed here).

Failure policy: fail open. A hook bug must never brick a Claude Code
session, so any unexpected error exits non-blocking with no output.
"""

import json
import os
import sys
from typing import Any, Iterator, Mapping

# High-precision defaults. IP_ADDRESS, DOB, and ZIP are deliberately
# excluded: version strings, dates, and 5-digit numbers saturate coding
# sessions and would make the firewall cry wolf (see DFPY-110).
DEFAULT_ENTITY_TYPES = ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"]

VALID_ACTIONS = {"ask", "deny"}

# Per-string scan cap, so a huge file write can't stall the hook. Applied
# per string (not shared across the payload) so a padding field can't starve
# the scan of later fields; TOTAL_SCAN_CHARS bounds the worst case overall.
MAX_SCAN_CHARS = 1_000_000
TOTAL_SCAN_CHARS = 8_000_000

_EXIT_OK = 0
# Exit 1 is Claude Code's non-blocking error: stderr is shown to the user,
# the tool call proceeds. Never exit 2 (blocking) on our own failures.
_EXIT_FAIL_OPEN = 1


def _entity_types(env: Mapping[str, str]) -> list[str]:
    raw = env.get("DATAFOG_HOOK_ENTITIES", "")
    parsed = [t.strip().upper() for t in raw.split(",") if t.strip()]
    # An empty parse (unset, or a value like " , ") must fall back to the
    # defaults: passing [] downstream would disable filtering entirely and
    # silently enable the noisy opt-in entity types.
    return parsed or DEFAULT_ENTITY_TYPES


def _action(env: Mapping[str, str]) -> str:
    action = env.get("DATAFOG_HOOK_ACTION", "ask").strip().lower()
    return action if action in VALID_ACTIONS else "ask"


def _csv_env(env: Mapping[str, str], name: str) -> list[str]:
    raw = env.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _iter_strings(value: Any) -> Iterator[str]:
    """Yield every string embedded in a JSON-like structure.

    Iterative (explicit stack), so adversarially deep nesting cannot
    trigger ``RecursionError`` and silently skip the scan.
    """
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            yield current
        elif isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)


def _scan_findings(
    value: Any,
    entity_types: list[str],
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
) -> dict[str, int]:
    """Scan all strings in ``value``; return counts per entity type."""
    import datafog

    counts: dict[str, int] = {}
    total_budget = TOTAL_SCAN_CHARS
    for text in _iter_strings(value):
        if total_budget <= 0:
            break
        chunk = text[: min(MAX_SCAN_CHARS, total_budget)]
        total_budget -= len(chunk)
        result = datafog.scan(
            chunk,
            engine="regex",
            entity_types=entity_types,
            allowlist=allowlist or None,
            allowlist_patterns=allowlist_patterns or None,
        )
        for entity in result.entities:
            counts[entity.type] = counts.get(entity.type, 0) + 1
    return counts


def _summary(counts: dict[str, int]) -> str:
    """Render findings without ever echoing the matched PII itself."""
    parts = [f"{etype} x{n}" for etype, n in sorted(counts.items())]
    return ", ".join(parts)


def _emit(event: str, fields: dict[str, Any]) -> str:
    return json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}})


def _handle_pre_tool_use(payload: dict, env: Mapping[str, str]) -> str:
    counts = _scan_findings(
        payload.get("tool_input"),
        _entity_types(env),
        allowlist=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST"),
        allowlist_patterns=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST_PATTERNS"),
    )
    if not counts:
        return ""
    tool = payload.get("tool_name", "tool")
    reason = (
        f"DataFog PII firewall: {tool} input contains {_summary(counts)}. "
        "Redact or tokenize these values before sending them anywhere."
    )
    return _emit(
        "PreToolUse",
        {"permissionDecision": _action(env), "permissionDecisionReason": reason},
    )


def _handle_user_prompt_submit(payload: dict, env: Mapping[str, str]) -> str:
    counts = _scan_findings(
        payload.get("prompt"),
        _entity_types(env),
        allowlist=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST"),
        allowlist_patterns=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST_PATTERNS"),
    )
    if not counts:
        return ""
    context = (
        f"DataFog PII firewall: the user's prompt contains {_summary(counts)}. "
        "Avoid repeating these values verbatim in responses, code, or files."
    )
    return _emit("UserPromptSubmit", {"additionalContext": context})


def _handle_post_tool_use(payload: dict, env: Mapping[str, str]) -> str:
    counts = _scan_findings(
        payload.get("tool_response"),
        _entity_types(env),
        allowlist=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST"),
        allowlist_patterns=_csv_env(env, "DATAFOG_HOOK_ALLOWLIST_PATTERNS"),
    )
    if not counts:
        return ""
    tool = payload.get("tool_name", "tool")
    context = (
        f"DataFog PII firewall: {tool} output contains {_summary(counts)}. "
        "Avoid repeating these values verbatim in responses, code, or files."
    )
    return _emit("PostToolUse", {"additionalContext": context})


_HANDLERS = {
    "PreToolUse": _handle_pre_tool_use,
    "UserPromptSubmit": _handle_user_prompt_submit,
    "PostToolUse": _handle_post_tool_use,
}


def run(payload: dict, env: Mapping[str, str]) -> tuple[int, str]:
    """Process one hook payload; return (exit_code, stdout). Fails open."""
    try:
        handler = _HANDLERS.get(payload.get("hook_event_name", ""))
        if handler is None:
            return _EXIT_OK, ""
        return _EXIT_OK, handler(payload, env)
    except Exception as exc:  # noqa: BLE001 — fail open by design
        print(f"datafog-hook error (fail-open): {exc}", file=sys.stderr)
        return _EXIT_FAIL_OPEN, ""


def main() -> None:
    """Console entry point: ``datafog-hook``."""
    # Catch everything, including RecursionError from json.load on
    # adversarially nested payloads: the fail-open contract applies to the
    # entire process, not just the handler.
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            payload = {}
    except Exception as exc:  # noqa: BLE001 — fail open by design
        print(f"datafog-hook: invalid hook payload (fail-open): {exc}", file=sys.stderr)
        sys.exit(_EXIT_FAIL_OPEN)

    code, stdout = run(payload, os.environ)
    if stdout:
        print(stdout)
    sys.exit(code)


if __name__ == "__main__":
    main()
