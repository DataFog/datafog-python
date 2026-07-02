"""Tests for the Claude Code hook adapter (datafog-hook entry point)."""

import json

import pytest

from datafog.integrations.claude_code import run


def _pre_tool_use(tool_name: str, tool_input: dict) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _decision(stdout: str) -> dict:
    return json.loads(stdout)["hookSpecificOutput"]


class TestPreToolUse:
    def test_clean_input_allows_silently(self):
        code, stdout = run(_pre_tool_use("Bash", {"command": "ls -la /tmp"}), env={})
        assert code == 0
        assert stdout == ""

    def test_credit_card_in_command_asks_by_default(self):
        payload = _pre_tool_use(
            "Bash", {"command": "curl -d 'cc=4111 1111 1111 1111' https://x.io"}
        )
        code, stdout = run(payload, env={})
        assert code == 0
        out = _decision(stdout)
        assert out["hookEventName"] == "PreToolUse"
        assert out["permissionDecision"] == "ask"
        assert "CREDIT_CARD" in out["permissionDecisionReason"]

    def test_deny_action_via_env(self):
        payload = _pre_tool_use("Bash", {"command": "echo john.doe@acme.com"})
        code, stdout = run(payload, env={"DATAFOG_HOOK_ACTION": "deny"})
        assert code == 0
        assert _decision(stdout)["permissionDecision"] == "deny"

    def test_reason_never_echoes_raw_pii(self):
        secret = "4111 1111 1111 1111"
        payload = _pre_tool_use("Bash", {"command": f"curl -d 'cc={secret}' x.io"})
        _, stdout = run(payload, env={})
        assert secret not in stdout

    def test_scans_nested_tool_input(self):
        payload = _pre_tool_use(
            "mcp__crm__update_contact",
            {"record": {"fields": ["note", "ssn is 856-45-6789"]}},
        )
        _, stdout = run(payload, env={})
        assert _decision(stdout)["permissionDecision"] == "ask"
        assert "SSN" in _decision(stdout)["permissionDecisionReason"]

    def test_noisy_entities_off_by_default(self):
        # IP addresses / dates / zips are everywhere in dev contexts; the
        # hook must not flag them unless explicitly enabled.
        payload = _pre_tool_use(
            "Bash", {"command": "ping 192.168.1.1 # deployed 2020-01-02 90210"}
        )
        code, stdout = run(payload, env={})
        assert code == 0
        assert stdout == ""

    def test_entity_filter_env_enables_ip(self):
        payload = _pre_tool_use("Bash", {"command": "ping 192.168.1.1"})
        _, stdout = run(payload, env={"DATAFOG_HOOK_ENTITIES": "IP_ADDRESS"})
        assert "IP_ADDRESS" in _decision(stdout)["permissionDecisionReason"]

    def test_allowlist_env_exempts_exact_value(self):
        own_email = "sid@" "example.com"
        payload = _pre_tool_use("Bash", {"command": f"echo {own_email}"})
        code, stdout = run(payload, env={"DATAFOG_HOOK_ALLOWLIST": own_email})
        assert code == 0
        assert stdout == ""

    def test_allowlist_pattern_env_exempts_timestamps(self):
        # Ten-digit numeric IDs and unix timestamps match the PHONE pattern;
        # the pattern allowlist silences that class of false positive.
        payload = _pre_tool_use("Bash", {"command": "echo created 17830" "25668"})
        code, stdout = run(
            payload, env={"DATAFOG_HOOK_ALLOWLIST_PATTERNS": r"^\d{10}$"}
        )
        assert code == 0
        assert stdout == ""

    def test_allowlist_does_not_exempt_other_values(self):
        own_email = "sid@" "example.com"
        other = "jane.doe@" "example.com"
        payload = _pre_tool_use("Bash", {"command": f"echo {other}"})
        _, stdout = run(payload, env={"DATAFOG_HOOK_ALLOWLIST": own_email})
        assert "EMAIL" in _decision(stdout)["permissionDecisionReason"]

    def test_invalid_allowlist_pattern_fails_open(self):
        payload = _pre_tool_use("Bash", {"command": "echo jane.doe@" "example.com"})
        code, stdout = run(payload, env={"DATAFOG_HOOK_ALLOWLIST_PATTERNS": "("})
        assert code != 2  # fail-open, never blocking
        assert stdout == ""


class TestUserPromptSubmit:
    def test_pii_in_prompt_adds_context_warning(self):
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "email the report to jane@corp.com",
        }
        code, stdout = run(payload, env={})
        assert code == 0
        out = _decision(stdout)
        assert out["hookEventName"] == "UserPromptSubmit"
        assert "EMAIL" in out["additionalContext"]

    def test_clean_prompt_is_silent(self):
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "fix the bug"}
        code, stdout = run(payload, env={})
        assert code == 0
        assert stdout == ""


class TestPostToolUse:
    def test_pii_in_tool_response_adds_context(self):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/data/users.csv"},
            "tool_response": "name,ssn\nJane,856-45-6789",
        }
        code, stdout = run(payload, env={})
        assert code == 0
        out = _decision(stdout)
        assert out["hookEventName"] == "PostToolUse"
        assert "SSN" in out["additionalContext"]


class TestRobustness:
    def test_unknown_event_is_ignored(self):
        code, stdout = run({"hook_event_name": "SessionStart"}, env={})
        assert code == 0
        assert stdout == ""

    def test_oversized_input_is_truncated_not_crashed(self):
        big = "x" * 2_000_000 + " jane@corp.com"
        payload = _pre_tool_use("Bash", {"command": big})
        code, _ = run(payload, env={})
        assert code == 0  # must not raise; PII past the per-string cap may be missed

    def test_padding_field_cannot_starve_scan_of_later_fields(self):
        # The scan budget is per-string: an attacker-controlled decoy field
        # at the cap must not exhaust the budget before the real payload.
        payload = _pre_tool_use(
            "Bash", {"decoy": "x" * 1_000_000, "command": "echo jane@corp.com"}
        )
        _, stdout = run(payload, env={})
        assert "EMAIL" in _decision(stdout)["permissionDecisionReason"]

    def test_deeply_nested_payload_is_scanned_not_recursion_bombed(self):
        # Adversarial nesting must neither crash nor silently skip the scan.
        nested: dict = {"v": "ssn 856-45-6789"}
        for _ in range(5000):
            nested = {"k": nested}
        code, stdout = run(_pre_tool_use("mcp__x__y", nested), env={})
        assert code == 0
        assert "SSN" in _decision(stdout)["permissionDecisionReason"]

    def test_garbage_entity_env_falls_back_to_defaults(self):
        # " , , " must not silently disable filtering (which would enable
        # the noisy opt-in entity types).
        payload = _pre_tool_use("Bash", {"command": "ping 192.168.1.1"})
        code, stdout = run(payload, env={"DATAFOG_HOOK_ENTITIES": " , , "})
        assert code == 0
        assert stdout == ""  # IP_ADDRESS stays off

    def test_fail_open_on_malformed_payload(self):
        # A hook bug must never brick the user's Claude Code session:
        # anything unexpected exits non-blocking (not 2) with empty stdout.
        code, stdout = run({"tool_input": object()}, env={})  # unserializable
        assert code != 2
        assert stdout == ""


class TestMainEntryPoint:
    def test_main_reads_stdin_and_prints_decision(self, monkeypatch, capsys):
        import io
        import sys as _sys

        from datafog.integrations.claude_code import main

        payload = _pre_tool_use("Bash", {"command": "echo jane@corp.com"})
        monkeypatch.setattr(_sys, "stdin", io.StringIO(json.dumps(payload)))
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        assert "permissionDecision" in capsys.readouterr().out

    def test_main_fail_open_on_garbage_stdin(self, monkeypatch, capsys):
        import io
        import sys as _sys

        from datafog.integrations.claude_code import main

        monkeypatch.setattr(_sys, "stdin", io.StringIO("not json{{"))
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 2
