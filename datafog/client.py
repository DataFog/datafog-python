"""
Client module for DataFog.

Provides CLI commands for scanning images and text using DataFog's OCR and PII detection capabilities.
"""

import asyncio
import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, List

import typer

from .config import OperationType, get_config
from .engine import scan as engine_scan
from .engine import scan_and_redact
from .main import DataFog
from .models import Entity, RedactResult, ScanResult
from .models.anonymizer import HashType

try:
    from .models.spacy_nlp import SpacyAnnotator
except ImportError:
    _SPACY_MISSING_MESSAGE = (
        "spaCy engine is not available. Install with: pip install datafog[nlp]"
    )

    class SpacyAnnotator:  # type: ignore[no-redef]
        """Fallback annotator used when spaCy optional dependency is missing."""

        def __init__(self, *_args, **_kwargs):
            raise ModuleNotFoundError(_SPACY_MISSING_MESSAGE)

        @staticmethod
        def download_model(_model_name: str):
            raise ModuleNotFoundError(_SPACY_MISSING_MESSAGE)

        @staticmethod
        def list_models():
            raise ModuleNotFoundError(_SPACY_MISSING_MESSAGE)

        @staticmethod
        def list_entities():
            raise ModuleNotFoundError(_SPACY_MISSING_MESSAGE)


app = typer.Typer()

CLI_SCHEMA_VERSION = "datafog.cli.v1"
CLI_RECORD_SCHEMA_VERSION = "datafog.cli.record.v1"
CLI_SUMMARY_SCHEMA_VERSION = "datafog.cli.summary.v1"

EXIT_OK = 0
EXIT_DETECTED = 1
EXIT_USAGE = 2
EXIT_PROCESSING = 3

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True, slots=True)
class AuditRecord:
    path: Path
    line: int
    record_index: int
    row: int | None
    field: str | None
    text: str


@dataclass(frozen=True, slots=True)
class AuditInputError:
    path: Path
    message: str
    line: int | None = None
    record_index: int | None = None
    row: int | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "line": self.line,
            "record_index": self.record_index,
            "row": self.row,
            "field": self.field,
            "message": self.message,
        }


def _entity_dicts(entities: Iterable[Entity], *, include_text: bool = False):
    return [entity.to_dict(include_text=include_text) for entity in entities]


def _summary(
    entities: Iterable[Entity],
    *,
    replacement_count: int | None = None,
    files_scanned: int | None = None,
    records_scanned: int | None = None,
) -> dict[str, object]:
    entity_list = list(entities)
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    highest_severity: str | None = None

    for entity in entity_list:
        by_type[entity.type] = by_type.get(entity.type, 0) + 1
        by_severity[entity.severity] = by_severity.get(entity.severity, 0) + 1
        if highest_severity is None or (
            SEVERITY_ORDER[entity.severity] > SEVERITY_ORDER[highest_severity]
        ):
            highest_severity = entity.severity

    payload: dict[str, object] = {
        "entity_count": len(entity_list),
        "by_type": by_type,
        "by_severity": by_severity,
        "highest_severity": highest_severity,
    }
    if replacement_count is not None:
        payload["replacement_count"] = replacement_count
    if files_scanned is not None:
        payload["files_scanned"] = files_scanned
    if records_scanned is not None:
        payload["records_scanned"] = records_scanned
    return payload


def _input_metadata(
    *,
    source: str,
    text: str | None = None,
    path: Path | None = None,
    records: int | None = None,
    file_count: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": source,
        "path": str(path) if path is not None else None,
        "records": records,
    }
    if text is not None:
        payload["bytes"] = len(text.encode("utf-8"))
    if file_count is not None:
        payload["file_count"] = file_count
    return payload


def _policy_metadata(
    *,
    preset: str,
    locale: str,
    include_text: bool,
    fail_on: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "preset": preset,
        "locale": locale,
        "include_text": include_text,
    }
    if fail_on is not None:
        payload["fail_on"] = fail_on
    return payload


def _emit_json(payload: dict[str, object], *, jsonl: bool = False) -> None:
    typer.echo(json.dumps(payload, separators=(",", ":") if jsonl else None))


def _fail_on_matches(
    entities: Iterable[Entity],
    *,
    fail_on_detect: bool = False,
    fail_on: str | None = None,
) -> bool:
    entity_list = list(entities)
    if fail_on_detect:
        return bool(entity_list)
    if fail_on is None:
        return False

    normalized = fail_on.lower().strip()
    if normalized in {"detect", "any"}:
        return bool(entity_list)
    if normalized not in SEVERITY_ORDER:
        allowed = ", ".join(["detect", *SEVERITY_ORDER])
        raise ValueError(f"--fail-on must be one of: {allowed}")
    threshold = SEVERITY_ORDER[normalized]
    return any(SEVERITY_ORDER[entity.severity] >= threshold for entity in entity_list)


def _exit_for_findings(
    entities: Iterable[Entity],
    *,
    fail_on_detect: bool = False,
    fail_on: str | None = None,
) -> int:
    return (
        EXIT_DETECTED
        if _fail_on_matches(
            entities,
            fail_on_detect=fail_on_detect,
            fail_on=fail_on,
        )
        else EXIT_OK
    )


def _read_cli_text(text: str | None, path: Path | None) -> tuple[str, str, Path | None]:
    if text is not None:
        return text, "argument", None
    if path is not None:
        return path.read_text(encoding="utf-8"), "file", path
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read()
        if stdin_text:
            return stdin_text, "stdin", None
    raise ValueError("Provide text, --file, or stdin.")


def _scan_payload(
    result: ScanResult,
    *,
    source: str,
    text: str,
    path: Path | None,
    preset: str,
    fail_on: str | None,
    exit_code: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": "scan",
        "ok": True,
        "input": _input_metadata(source=source, text=text, path=path, records=None),
        "policy": _policy_metadata(
            preset=preset,
            locale=result.locale,
            include_text=result.include_text,
            fail_on=fail_on,
        ),
        "summary": _summary(result.entities),
        "entities": _entity_dicts(result.entities, include_text=result.include_text),
        "errors": [],
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    return payload


def _redact_payload(
    result: RedactResult,
    *,
    source: str,
    text: str,
    path: Path | None,
    preset: str,
    locale: str,
    include_text: bool,
    fail_on: str | None,
    exit_code: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": "redact",
        "ok": True,
        "input": _input_metadata(source=source, text=text, path=path, records=None),
        "policy": _policy_metadata(
            preset=preset,
            locale=locale,
            include_text=include_text,
            fail_on=fail_on,
        ),
        "summary": _summary(
            result.entities,
            replacement_count=len(result.replacements),
        ),
        "redacted_text": result.redacted_text,
        "entities": _entity_dicts(result.entities, include_text=include_text),
        "replacements": [replacement.to_dict() for replacement in result.replacements],
        "session": {
            "session_id": result.session_id,
            "reversible": result.session_id is not None,
            "mapping_count": 0,
        },
        "errors": [],
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    return payload


def _iter_audit_records(path: Path):
    files = (
        [path]
        if path.is_file()
        else sorted(item for item in path.rglob("*") if item.is_file())
    )
    for file_path in files:
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            yield from _iter_csv_audit_records(file_path)
        else:
            yield from _iter_text_audit_records(file_path, jsonl=suffix == ".jsonl")


def _iter_text_audit_records(file_path: Path, *, jsonl: bool):
    with file_path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n\r")
            record_index = line_number - 1
            if jsonl:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    yield AuditInputError(
                        path=file_path,
                        line=line_number,
                        record_index=record_index,
                        message=(
                            f"Malformed JSONL at line {line_number}: {exc.msg}. "
                            "Scanned raw line as text."
                        ),
                    )
                    yield AuditRecord(
                        path=file_path,
                        line=line_number,
                        record_index=record_index,
                        row=None,
                        field=None,
                        text=line,
                    )
                    continue

                if isinstance(record, dict):
                    for field, value in record.items():
                        if isinstance(value, str):
                            yield AuditRecord(
                                path=file_path,
                                line=line_number,
                                record_index=record_index,
                                row=None,
                                field=str(field),
                                text=value,
                            )
                    continue

            yield AuditRecord(
                path=file_path,
                line=line_number,
                record_index=record_index,
                row=None,
                field=None,
                text=line,
            )


def _iter_csv_audit_records(file_path: Path):
    try:
        with file_path.open(encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return

            for record_index, row in enumerate(reader):
                row_number = record_index + 1
                line_number = reader.line_num
                for field, value in row.items():
                    if field is None:
                        extra_values = [
                            str(item) for item in value or [] if item is not None
                        ]
                        if not extra_values:
                            continue
                        yield AuditInputError(
                            path=file_path,
                            line=line_number,
                            record_index=record_index,
                            row=row_number,
                            message=(
                                "CSV row has more columns than the header. "
                                "Scanned extra values as _extra."
                            ),
                        )
                        yield AuditRecord(
                            path=file_path,
                            line=line_number,
                            record_index=record_index,
                            row=row_number,
                            field="_extra",
                            text=" ".join(extra_values),
                        )
                        continue

                    yield AuditRecord(
                        path=file_path,
                        line=line_number,
                        record_index=record_index,
                        row=row_number,
                        field=str(field),
                        text=value or "",
                    )
    except csv.Error as exc:
        yield AuditInputError(
            path=file_path,
            message=f"Malformed CSV: {exc}",
        )


def _audit_summary(
    entities: Iterable[Entity],
    *,
    findings: list[dict[str, object]],
    files_scanned: int,
    records_scanned: int,
    fields_scanned: int,
) -> dict[str, object]:
    payload = _summary(
        entities,
        files_scanned=files_scanned,
        records_scanned=records_scanned,
    )
    by_file: dict[str, int] = {}
    by_field: dict[str, int] = {}
    files_with_findings: set[str] = set()
    fields_with_findings: set[str] = set()
    records_with_findings: set[tuple[str, int | None]] = set()

    for finding in findings:
        path = str(finding["path"])
        field = finding.get("field")
        record_index = finding.get("record_index")

        by_file[path] = by_file.get(path, 0) + 1
        files_with_findings.add(path)
        records_with_findings.add(
            (path, record_index if isinstance(record_index, int) else None)
        )

        if field is not None:
            field_name = str(field)
            by_field[field_name] = by_field.get(field_name, 0) + 1
            fields_with_findings.add(field_name)

    payload.update(
        {
            "fields_scanned": fields_scanned,
            "files_with_findings": len(files_with_findings),
            "records_with_findings": len(records_with_findings),
            "fields_with_findings": len(fields_with_findings),
            "by_file": by_file,
            "by_field": by_field,
        }
    )
    return payload


def _audit_payload(
    *,
    path: Path,
    preset: str,
    locale: str,
    include_text: bool,
    fail_on: str | None,
    exit_code: int,
    files_scanned: int,
    records_scanned: int,
    fields_scanned: int,
    all_entities: list[Entity],
    findings: list[dict[str, object]],
    errors: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": "audit",
        "ok": True,
        "exit_code": exit_code,
        "input": _input_metadata(
            source="directory" if path.is_dir() else "file",
            path=path,
            file_count=files_scanned,
            records=records_scanned,
        ),
        "policy": _policy_metadata(
            preset=preset,
            locale=locale,
            include_text=include_text,
            fail_on=fail_on,
        ),
        "summary": _audit_summary(
            all_entities,
            findings=findings,
            files_scanned=files_scanned,
            records_scanned=records_scanned,
            fields_scanned=fields_scanned,
        ),
        "findings": findings,
        "errors": errors,
    }


@app.command("scan")
def scan_command(
    text: str | None = typer.Argument(None, help="Text to scan"),
    file: Path | None = typer.Option(None, "--file", "-f", help="File to scan"),
    preset: str = typer.Option("default", "--preset", help="Policy preset"),
    engine: str = typer.Option("regex", "--engine", help="Detection engine"),
    locale: str = typer.Option("global", "--locale", help="Locale policy"),
    include_text: bool = typer.Option(
        False,
        "--include-text",
        help="Include raw matched text when policy allows it",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit datafog.cli.v1 JSON",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit one datafog.cli.record.v1 JSON object",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help="Exit 1 when findings meet severity: low, medium, high, critical, detect",
    ),
    fail_on_detect: bool = typer.Option(
        False,
        "--fail-on-detect",
        help="Exit 1 when any entity is detected",
    ),
):
    """Scan text with the v5 CLI contract."""
    try:
        input_text, source, input_path = _read_cli_text(text, file)
        result = engine_scan(
            input_text,
            engine=engine,
            include_text=include_text,
            locale=locale,
            policy=preset,
        )
        exit_code = _exit_for_findings(
            result.entities,
            fail_on_detect=fail_on_detect,
            fail_on=fail_on,
        )
        if jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_RECORD_SCHEMA_VERSION,
                    "command": "scan",
                    "path": str(input_path) if input_path is not None else None,
                    "record_index": 0,
                    "summary": _summary(result.entities),
                    "entities": _entity_dicts(
                        result.entities,
                        include_text=result.include_text,
                    ),
                    "errors": [],
                },
                jsonl=True,
            )
        elif json_output:
            _emit_json(
                _scan_payload(
                    result,
                    source=source,
                    text=input_text,
                    path=input_path,
                    preset=preset,
                    fail_on=fail_on or ("detect" if fail_on_detect else None),
                    exit_code=exit_code,
                )
            )
        else:
            typer.echo(f"Found {len(result.entities)} entities.")
            for entity in result.entities:
                typer.echo(
                    f"{entity.type} {entity.start}:{entity.end} "
                    f"{entity.severity} {entity.detector}"
                )
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except ValueError as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "scan",
                    "ok": False,
                    "input": {},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(str(exc), err=True)
        raise typer.Exit(code=EXIT_USAGE) from exc
    except Exception as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "scan",
                    "ok": False,
                    "input": {},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING) from exc


@app.command("redact")
def redact_command(
    text: str | None = typer.Argument(None, help="Text to redact"),
    file: Path | None = typer.Option(None, "--file", "-f", help="File to redact"),
    preset: str = typer.Option("llm", "--preset", help="Policy preset"),
    engine: str = typer.Option("regex", "--engine", help="Detection engine"),
    locale: str = typer.Option("global", "--locale", help="Locale policy"),
    include_text: bool = typer.Option(
        False,
        "--include-text",
        help="Include raw matched text when policy allows it",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit datafog.cli.v1 JSON",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit one datafog.cli.record.v1 JSON object",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help="Exit 1 when findings meet severity: low, medium, high, critical, detect",
    ),
    fail_on_detect: bool = typer.Option(
        False,
        "--fail-on-detect",
        help="Exit 1 when any entity is detected",
    ),
    hash_key_file: Path | None = typer.Option(
        None,
        "--hash-key-file",
        help="File containing the HMAC key for hmac/hash policies",
    ),
):
    """Redact text with the v5 CLI contract."""
    try:
        input_text, source, input_path = _read_cli_text(text, file)
        hash_key = (
            hash_key_file.read_text(encoding="utf-8").strip()
            if hash_key_file is not None
            else None
        )
        result = scan_and_redact(
            text=input_text,
            engine=engine,
            locale=locale,
            include_text=include_text,
            policy=preset,
            hash_key=hash_key,
        )
        effective_include_text = any(
            entity.text is not None for entity in result.entities
        )
        exit_code = _exit_for_findings(
            result.entities,
            fail_on_detect=fail_on_detect,
            fail_on=fail_on,
        )
        if jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_RECORD_SCHEMA_VERSION,
                    "command": "redact",
                    "path": str(input_path) if input_path is not None else None,
                    "record_index": 0,
                    "summary": _summary(
                        result.entities,
                        replacement_count=len(result.replacements),
                    ),
                    "redacted_text": result.redacted_text,
                    "entities": _entity_dicts(
                        result.entities,
                        include_text=effective_include_text,
                    ),
                    "replacements": [
                        replacement.to_dict() for replacement in result.replacements
                    ],
                    "errors": [],
                },
                jsonl=True,
            )
        elif json_output:
            _emit_json(
                _redact_payload(
                    result,
                    source=source,
                    text=input_text,
                    path=input_path,
                    preset=preset,
                    locale=locale,
                    include_text=effective_include_text,
                    fail_on=fail_on or ("detect" if fail_on_detect else None),
                    exit_code=exit_code,
                )
            )
        else:
            typer.echo(result.redacted_text)
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except ValueError as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "redact",
                    "ok": False,
                    "input": {},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(str(exc), err=True)
        raise typer.Exit(code=EXIT_USAGE) from exc
    except Exception as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "redact",
                    "ok": False,
                    "input": {},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING) from exc


@app.command("audit")
def audit_command(
    path: Path = typer.Argument(..., help="File or directory to audit"),
    preset: str = typer.Option("logs", "--preset", help="Policy preset"),
    engine: str = typer.Option("regex", "--engine", help="Detection engine"),
    locale: str = typer.Option("global", "--locale", help="Locale policy"),
    include_text: bool = typer.Option(
        False,
        "--include-text",
        help="Include raw matched text when policy allows it",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit datafog.cli.v1 JSON",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit datafog.cli.record.v1 JSON lines",
    ),
    emit_summary: bool = typer.Option(
        False,
        "--emit-summary",
        help="Emit a final datafog.cli.summary.v1 JSONL record",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help="Exit 1 when findings meet severity: low, medium, high, critical, detect",
    ),
    fail_on_detect: bool = typer.Option(
        False,
        "--fail-on-detect",
        help="Exit 1 when any entity is detected",
    ),
):
    """Audit files or directories with the v5 CLI contract."""
    try:
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not path.is_file() and not path.is_dir():
            raise ValueError(f"Path must be a file or directory: {path}")

        file_paths = (
            [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        )
        records_seen: set[tuple[str, int]] = set()
        fields_scanned = 0
        all_entities: list[Entity] = []
        findings: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []

        for audit_item in _iter_audit_records(path):
            if isinstance(audit_item, AuditInputError):
                error_payload = audit_item.to_dict()
                errors.append(error_payload)
                if jsonl_output:
                    _emit_json(
                        {
                            "schema_version": CLI_RECORD_SCHEMA_VERSION,
                            "command": "audit",
                            "path": str(audit_item.path),
                            "line": audit_item.line,
                            "record_index": audit_item.record_index,
                            "row": audit_item.row,
                            "field": audit_item.field,
                            "summary": _summary([]),
                            "entities": [],
                            "errors": [error_payload],
                        },
                        jsonl=True,
                    )
                continue

            fields_scanned += 1
            records_seen.add((str(audit_item.path), audit_item.record_index))
            result = engine_scan(
                audit_item.text,
                engine=engine,
                include_text=include_text,
                locale=locale,
                policy=preset,
            )
            all_entities.extend(result.entities)
            if result.entities:
                record_summary = _summary(result.entities)
                if jsonl_output:
                    _emit_json(
                        {
                            "schema_version": CLI_RECORD_SCHEMA_VERSION,
                            "command": "audit",
                            "path": str(audit_item.path),
                            "line": audit_item.line,
                            "record_index": audit_item.record_index,
                            "row": audit_item.row,
                            "field": audit_item.field,
                            "summary": record_summary,
                            "entities": _entity_dicts(
                                result.entities,
                                include_text=result.include_text,
                            ),
                            "errors": [],
                        },
                        jsonl=True,
                    )
                for entity in result.entities:
                    findings.append(
                        {
                            "path": str(audit_item.path),
                            "line": audit_item.line,
                            "record_index": audit_item.record_index,
                            "row": audit_item.row,
                            "field": audit_item.field,
                            "entity": entity.to_dict(
                                include_text=result.include_text,
                            ),
                        }
                    )

        exit_code = _exit_for_findings(
            all_entities,
            fail_on_detect=fail_on_detect,
            fail_on=fail_on,
        )
        records_scanned = len(records_seen)
        fail_policy = fail_on or ("detect" if fail_on_detect else None)
        if jsonl_output:
            if emit_summary:
                _emit_json(
                    {
                        "schema_version": CLI_SUMMARY_SCHEMA_VERSION,
                        "command": "audit",
                        "summary": _audit_summary(
                            all_entities,
                            findings=findings,
                            files_scanned=len(file_paths),
                            records_scanned=records_scanned,
                            fields_scanned=fields_scanned,
                        ),
                        "errors": errors,
                    },
                    jsonl=True,
                )
        elif json_output:
            _emit_json(
                _audit_payload(
                    path=path,
                    preset=preset,
                    locale=locale,
                    include_text=include_text,
                    fail_on=fail_policy,
                    exit_code=exit_code,
                    files_scanned=len(file_paths),
                    records_scanned=records_scanned,
                    fields_scanned=fields_scanned,
                    all_entities=all_entities,
                    findings=findings,
                    errors=errors,
                )
            )
        else:
            typer.echo(
                f"Scanned {len(file_paths)} files and {records_scanned} records; "
                f"found {len(all_entities)} entities."
            )
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except ValueError as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "audit",
                    "ok": False,
                    "input": {"path": str(path)},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(str(exc), err=True)
        raise typer.Exit(code=EXIT_USAGE) from exc
    except Exception as exc:
        if json_output or jsonl_output:
            _emit_json(
                {
                    "schema_version": CLI_SCHEMA_VERSION,
                    "command": "audit",
                    "ok": False,
                    "input": {"path": str(path)},
                    "policy": {"preset": preset, "locale": locale},
                    "summary": {},
                    "errors": [{"message": str(exc)}],
                },
                jsonl=jsonl_output,
            )
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=EXIT_PROCESSING) from exc


@app.command()
def scan_image(
    image_urls: List[str] = typer.Argument(
        None, help="List of image URLs or file paths to extract text from"
    ),
    operations: str = typer.Option("scan", help="Operation to perform"),
):
    """
    Scan images for text and PII.

    Extracts text from images using OCR, then detects PII entities.
    Handles both remote URLs and local file paths.

    Args:
        image_urls: List of image URLs or file paths
        operations: Pipeline operations to run (default: scan)

    Prints results or exits with error on failure.
    """
    if not image_urls:
        typer.echo("No image URLs or file paths provided. Please provide at least one.")
        raise typer.Exit(code=1)

    logging.basicConfig(level=logging.INFO)
    # Convert comma-separated string operations to a list of OperationType objects
    operation_list = [OperationType(op.strip()) for op in operations.split(",")]
    ocr_client = DataFog(operations=operation_list)
    try:
        results = asyncio.run(ocr_client.run_ocr_pipeline(image_urls=image_urls))
        typer.echo(f"OCR Pipeline Results: {results}")

        try:
            from .telemetry import track_function_call

            track_function_call(
                function_name="scan_image",
                module="datafog.client",
                source="cli",
                batch_size=len(image_urls),
            )
        except Exception:
            pass
    except Exception as e:
        logging.exception("Error in run_ocr_pipeline")
        try:
            from .telemetry import track_error

            track_error("scan_image", type(e).__name__, source="cli")
        except Exception:
            pass
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def scan_text(
    str_list: List[str] = typer.Argument(
        None, help="List of texts to extract text from"
    ),
    operations: str = typer.Option("scan", help="Operation to perform"),
):
    """
    Scan texts for PII.

    Detects PII entities in a list of input texts.

    Args:
        str_list: List of texts to analyze
        operations: Pipeline operations to run (default: scan)

    Prints results or exits with error on failure.
    """
    if not str_list:
        typer.echo("No texts provided.")
        raise typer.Exit(code=1)

    logging.basicConfig(level=logging.INFO)
    # Convert comma-separated string operations to a list of OperationType objects
    operation_list = [OperationType(op.strip()) for op in operations.split(",")]
    text_client = DataFog(operations=operation_list)
    try:
        results = text_client.run_text_pipeline_sync(str_list=str_list)
        typer.echo(f"Text Pipeline Results: {results}")

        try:
            from .telemetry import track_function_call

            track_function_call(
                function_name="scan_text",
                module="datafog.client",
                source="cli",
                batch_size=len(str_list),
                operations=[op.value for op in operation_list],
            )
        except Exception:
            pass
    except Exception as e:
        logging.exception("Text pipeline error")
        try:
            from .telemetry import track_error

            track_error("scan_text", type(e).__name__, source="cli")
        except Exception:
            pass
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def health():
    """
    Check DataFog service health.

    Prints a message indicating that DataFog is running.
    """
    typer.echo("DataFog is running.")


@app.command()
def show_config():
    """
    Show current configuration.

    Prints the current DataFog configuration.
    """
    typer.echo(get_config())


@app.command()
def download_model(
    model_name: str = typer.Argument(..., help="Model to download"),
    engine: str = typer.Option("spacy", help="Engine type (spacy, gliner)"),
):
    """
    Download a model for specified engine.

    Examples:
        spaCy: datafog download-model en_core_web_lg --engine spacy
        GLiNER: datafog download-model urchade/gliner_multi_pii-v1 --engine gliner
    """
    if engine == "spacy":
        try:
            SpacyAnnotator.download_model(model_name)
            typer.echo(f"SpaCy model {model_name} downloaded successfully.")
        except ModuleNotFoundError as e:
            typer.echo(str(e))
            raise typer.Exit(code=1)

    elif engine == "gliner":
        try:
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            GLiNERAnnotator.download_model(model_name)
            typer.echo(f"GLiNER model {model_name} downloaded and cached successfully.")
        except ImportError:
            typer.echo(
                "GLiNER not available. Install with: pip install datafog[nlp-advanced]"
            )
            raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Error downloading GLiNER model {model_name}: {str(e)}")
            raise typer.Exit(code=1)

    else:
        typer.echo(f"Unknown engine: {engine}. Supported engines: spacy, gliner")
        raise typer.Exit(code=1)


@app.command()
def show_spacy_model_directory(
    model_name: str = typer.Argument(None, help="Model to check")
):
    """
    Show the directory path for a spaCy model.

    Args:
        model_name: Name of the model to check.

    Prints the directory path of the specified model.
    """
    if not model_name:
        typer.echo("No model name provided to check.")
        raise typer.Exit(code=1)

    try:
        annotator = SpacyAnnotator(model_name)
        typer.echo(annotator.show_model_path())
    except ModuleNotFoundError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)


@app.command()
def list_spacy_models():
    """
    List available spaCy models.

    Prints a list of all available spaCy models.
    """
    try:
        annotator = SpacyAnnotator()
        typer.echo(annotator.list_models())
    except ModuleNotFoundError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)


@app.command()
def list_models(
    engine: str = typer.Option(
        "spacy", help="Engine to list models for (spacy, gliner)"
    )
):
    """
    List available models for specified engine.

    Examples:
        datafog list-models --engine spacy
        datafog list-models --engine gliner
    """
    if engine == "spacy":
        try:
            annotator = SpacyAnnotator()
            typer.echo("Available spaCy models:")
            typer.echo(annotator.list_models())
        except ModuleNotFoundError as e:
            typer.echo(str(e))
            raise typer.Exit(code=1)

    elif engine == "gliner":
        typer.echo("Popular GLiNER models:")
        models = [
            "urchade/gliner_base (recommended starting point)",
            "urchade/gliner_multi_pii-v1 (specialized for PII detection)",
            "urchade/gliner_large-v2 (higher accuracy)",
            "knowledgator/modern-gliner-bi-large-v1.0 (4x faster, modern)",
            "urchade/gliner_medium-v2.1 (balanced size/performance)",
        ]
        for model in models:
            typer.echo(f"  • {model}")
        typer.echo("\nSee more at: https://huggingface.co/models?search=gliner")

    else:
        typer.echo(f"Unknown engine: {engine}. Supported engines: spacy, gliner")
        raise typer.Exit(code=1)


@app.command()
def list_entities():
    """
    List available entities.

    Prints a list of all available entities that can be recognized.
    """
    try:
        annotator = SpacyAnnotator()
        typer.echo(annotator.list_entities())
    except ModuleNotFoundError as e:
        try:
            from .processing.text_processing.spacy_pii_annotator import (
                PII_ANNOTATION_LABELS,
            )

            typer.echo(PII_ANNOTATION_LABELS)
        except Exception:
            typer.echo(str(e))
            raise typer.Exit(code=1)


@app.command()
def redact_text(text: str = typer.Argument(None, help="Text to redact")):
    """
    Redact PII in text.

    Args:
        text: Text to redact.

    Prints the redacted text.
    """
    if not text:
        typer.echo("No text provided to redact.")
        raise typer.Exit(code=1)

    result = scan_and_redact(text=text, engine="smart", strategy="token")
    typer.echo(result.redacted_text)

    try:
        from .telemetry import track_function_call

        track_function_call(
            function_name="redact_text",
            module="datafog.client",
            source="cli",
            method="redact",
        )
    except Exception:
        pass


@app.command()
def replace_text(text: str = typer.Argument(None, help="Text to replace PII")):
    """
    Replace PII in text with anonymized values.

    Args:
        text: Text to replace PII.

    Prints the text with PII replaced.
    """
    if not text:
        typer.echo("No text provided to replace PII.")
        raise typer.Exit(code=1)

    result = scan_and_redact(text=text, engine="smart", strategy="pseudonymize")
    typer.echo(result.redacted_text)

    try:
        from .telemetry import track_function_call

        track_function_call(
            function_name="replace_text",
            module="datafog.client",
            source="cli",
            method="replace",
        )
    except Exception:
        pass


@app.command()
def hash_text(
    text: str = typer.Argument(None, help="Text to hash PII"),
    hash_type: HashType = typer.Option(HashType.SHA256, help="Hash algorithm to use"),
    hash_key_file: Path | None = typer.Option(
        None,
        help=("File containing the HMAC key. DATAFOG_HMAC_KEY is used when omitted."),
    ),
):
    """
    Choose from SHA256, MD5, or SHA3-256 algorithms to hash detected PII in text.

    Args:
        text: Text to hash PII.
        hash_type: Hash algorithm to use.

    Prints the text with PII hashed.
    """
    if not text:
        typer.echo("No text provided to hash.")
        raise typer.Exit(code=1)

    hash_key = hash_key_file.read_text().strip() if hash_key_file is not None else None

    # HashType is retained for backward-compatible CLI signature.
    _ = hash_type
    try:
        result = scan_and_redact(
            text=text,
            engine="smart",
            strategy="hash",
            hash_key=hash_key,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(result.redacted_text)

    try:
        from .telemetry import track_function_call

        track_function_call(
            function_name="hash_text",
            module="datafog.client",
            source="cli",
            method="hash",
            hash_type=hash_type.value,
        )
    except Exception:
        pass


if __name__ == "__main__":
    app()
