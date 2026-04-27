"""Tests for the v5 machine-readable CLI contract."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from datafog.client import app

runner = CliRunner()


def _json(stdout: str) -> dict:
    return json.loads(stdout)


def test_scan_json_contract_is_safe_by_default() -> None:
    result = runner.invoke(
        app,
        ["scan", "Email jane@example.com", "--engine", "regex", "--json"],
    )

    assert result.exit_code == 0
    payload = _json(result.stdout)
    assert payload["schema_version"] == "datafog.cli.v1"
    assert payload["command"] == "scan"
    assert payload["ok"] is True
    assert payload["input"]["source"] == "argument"
    assert payload["input"]["records"] is None
    assert payload["summary"]["entity_count"] == 1
    assert payload["summary"]["by_type"] == {"EMAIL": 1}
    assert payload["entities"][0]["text"] is None
    assert "jane@example.com" not in json.dumps(payload["input"])


def test_scan_json_fail_on_detect_exits_one() -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            "Email jane@example.com",
            "--engine",
            "regex",
            "--json",
            "--fail-on-detect",
        ],
    )

    assert result.exit_code == 1
    payload = _json(result.stdout)
    assert payload["exit_code"] == 1
    assert payload["policy"]["fail_on"] == "detect"


def test_redact_json_contract_includes_replacements_without_raw_mapping() -> None:
    result = runner.invoke(
        app,
        ["redact", "Email jane@example.com", "--engine", "regex", "--json"],
    )

    assert result.exit_code == 0
    payload = _json(result.stdout)
    assert payload["schema_version"] == "datafog.cli.v1"
    assert payload["command"] == "redact"
    assert payload["input"]["records"] is None
    assert payload["redacted_text"] == "Email [EMAIL_1]"
    assert payload["replacements"][0]["replacement"] == "[EMAIL_1]"
    assert payload["session"]["reversible"] is False
    assert payload["session"]["mapping_count"] == 0
    assert payload["entities"][0]["text"] is None


def test_audit_json_contract_and_fail_on(tmp_path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text("safe line\nemail jane@example.com\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "audit",
            str(log_file),
            "--engine",
            "regex",
            "--json",
            "--fail-on",
            "high",
        ],
    )

    assert result.exit_code == 1
    payload = _json(result.stdout)
    assert payload["schema_version"] == "datafog.cli.v1"
    assert payload["command"] == "audit"
    assert payload["exit_code"] == 1
    assert payload["input"]["source"] == "file"
    assert payload["summary"]["records_scanned"] == 2
    assert payload["summary"]["by_type"] == {"EMAIL": 1}
    assert payload["findings"][0]["line"] == 2
    assert payload["findings"][0]["entity"]["text"] is None


def test_audit_jsonl_contract_and_summary(tmp_path) -> None:
    data_file = tmp_path / "records.jsonl"
    data_file.write_text(
        '{"message":"safe"}\n{"message":"email jane@example.com"}\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "audit",
            str(data_file),
            "--engine",
            "regex",
            "--jsonl",
            "--emit-summary",
        ],
    )

    assert result.exit_code == 0
    lines = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(lines) == 2
    assert lines[0]["schema_version"] == "datafog.cli.record.v1"
    assert lines[0]["command"] == "audit"
    assert lines[0]["line"] == 2
    assert lines[0]["field"] == "message"
    assert lines[0]["summary"]["entity_count"] == 1
    assert lines[1]["schema_version"] == "datafog.cli.summary.v1"
    assert lines[1]["summary"]["records_scanned"] == 2


def test_cli_json_usage_error_exits_two() -> None:
    result = runner.invoke(app, ["scan", "--json"])

    assert result.exit_code == 2
    payload = _json(result.stdout)
    assert payload["ok"] is False
    assert "Provide text" in payload["errors"][0]["message"]
