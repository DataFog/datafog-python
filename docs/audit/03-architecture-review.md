# Phase 3 - Architecture Review

Date: 2026-02-13

## 3.1 Internal API Analysis (Call Paths)

### Path A: `DataFog().scan_text("some text")`

- Actual behavior: **method does not exist** on `datafog.main.DataFog`.
- Verified result: `AttributeError: 'DataFog' object has no attribute 'scan_text'`.
- Sync/async: N/A (fails before execution).
- Error handling: no compatibility shim.

### Path B: `DataFog(operations=["scan", "redact"]).process_text("some text")`

- Actual behavior: **`process_text` does not exist** on `datafog.main.DataFog`.
- `operations=["scan", "redact"]` is accepted at runtime but values are plain strings, while code checks `OperationType` enums in pipeline branches.
- Sync/async: N/A (method missing).
- Error handling: no compatibility shim; silent type mismatch risk in `operations`.

### Path C: `TextService(engine="gliner").annotate_text_sync("some text")`

Call chain:

1. `TextService.__init__(engine="gliner")`
2. `_ensure_gliner_available()` (imports module, not actual GLiNER runtime dependency)
3. `annotate_text_sync()`
4. `_annotate_single_chunk()`
5. `gliner_annotator` property
6. `_create_gliner_annotator()`
7. `GLiNERAnnotator.create()` -> `from gliner import GLiNER` -> `GLiNER.from_pretrained(...)`
8. `GLiNERAnnotator.annotate()`

Branches:

- If `gliner` import/model load fails inside `create()`, `_create_gliner_annotator()` returns `None`.
- `_annotate_single_chunk()` then raises `ImportError("GLiNER engine not available...")`.

Error points:

- Model download/load failures.
- Inconsistent dependency validation at init (init can succeed even without GLiNER runtime).

Sync/async:

- Entire path is synchronous.

### Path D: `TextService(engine="smart").annotate_text_sync("some text")`

Call chain:

1. `TextService.__init__(engine="smart")`
2. `_ensure_gliner_available()` (module-level check only)
3. `annotate_text_sync()`
4. `_annotate_single_chunk()` -> `_annotate_with_smart_cascade()`
5. Stage 1: `regex_annotator.annotate(...)`
6. Stage 2 (conditional): `gliner_annotator.annotate(...)`
7. Stage 3 (conditional): `spacy_annotator.annotate(...)`

Branches:

- Cascade stop conditions:
  - regex stage stops on `>=1` detected entity
  - gliner stage stops on `>=2` entities
- If GLiNER unavailable, stage 2 is skipped; it silently falls back.
- If spaCy unavailable, stage 3 is skipped; final fallback is regex or GLiNER.

Error points:

- No explicit warning when smart degrades due missing ML deps.
- Regex false positives can short-circuit smart and suppress NER.

Sync/async:

- Synchronous.

### Path E: `datafog scan-text "some text"` (CLI)

Call chain:

1. `datafog.client.scan_text` (Typer command)
2. Parse operations string -> `OperationType(...)` list
3. Instantiate `datafog.main.DataFog`
4. `DataFog.run_text_pipeline_sync(str_list=[...])`
5. `RegexAnnotator.annotate(...)` per text
6. Optional anonymization branch in `run_text_pipeline_sync`

Branches:

- If `OperationType.SCAN` absent: returns original texts.
- If anonymization ops present: converts spans to `AnnotationResult`, runs `Anonymizer`.

Error points:

- `OperationType` conversion failures.
- Runtime regex anomalies (e.g., empty `IP_ADDRESS` matches).

Sync/async:

- Fully synchronous.

### Path F: `datafog redact-text "some text"` (CLI)

Call chain:

1. `datafog.client.redact_text`
2. `SpacyAnnotator()` (`datafog.models.spacy_nlp.SpacyAnnotator`)
3. `SpacyAnnotator.annotate_text(...)` (loads/downloads model if needed)
4. `Anonymizer(anonymizer_type=REDACT).anonymize(...)`
5. `Anonymizer.redact_pii(...)`

Branches:

- Model download path triggers if spaCy model package missing.

Error points:

- spaCy model/network dependency.
- CLI command has no protective try/except around annotation path.

Sync/async:

- Synchronous.

## 3.2 Minimum Core Interface vs Current State

Target internal boundary (needed by MCP proxy and future Rust core):

- `scan(text, engine, entity_types) -> ScanResult`
- `redact(text, entities, strategy) -> RedactResult`

Current state:

- No single internal interface module.
- Behavior is split across:
  - `datafog.core` convenience functions
  - `datafog.main.DataFog` class methods
  - `datafog.services.text_service.TextService`
  - CLI-specific direct usage paths
- Output contracts vary by path:
  - dicts of lists
  - span lists
  - class-specific models
  - plain strings

Gap summary:

- Missing canonical entity datamodel (`type`, `text`, `start`, `end`, `confidence`, `engine`).
- Missing canonical scan/redact result objects.
- No single delegation path for all public APIs.
- Legacy and lean/original variants create inconsistent semantics.

Refactor required:

- Add `datafog/engine.py` as sole internal entry point.
- Make existing public APIs (`DataFog`, `TextService`, CLI) thin wrappers around engine functions.
- Normalize entity type mapping across engines at one boundary.

## 3.3 Dependency Graph

High-level import graph:

- `datafog.__init__` -> `core`, `main`, `services.text_service`, `client`, `telemetry`, model modules.
- `client` -> `main`, `models.anonymizer`, `models.spacy_nlp`, optional GLiNER module.
- `main` -> `config`, `models.anonymizer`, regex annotator.
- `core` -> `services.text_service`, model modules, telemetry.
- `services.text_service` -> regex annotator, spaCy annotator, GLiNER annotator, telemetry.
- `services.image_service` -> Donut + pytesseract processors.
- `main_original` -> image/text/spark services + spaCy annotator.

Cycle check:

- No direct circular import cycles detected in current module graph.

Heavy imports at module load (risk):

- `datafog/models/spacy_nlp.py` imports `spacy` and `rich` at top-level.
- `datafog/services/image_service.py` imports `aiohttp`, `certifi`, `PIL` and OCR processors at top-level.
- `datafog/processing/image_processing/donut_processor.py` imports `numpy`, `PIL` at top-level.
- `datafog/processing/text_processing/__init__.py` imports spaCy annotator eagerly.

## 3.4 Optional Dependency Handling (Core-Only Install Audit)

Environment created with core-only install (`pip install .` in a fresh venv).

Observed behavior:

- `from datafog import DataFog; DataFog().detect("john@example.com")` -> works (regex path).
- `DataFog().scan_text("john@example.com")` -> fails (`AttributeError`, method missing).
- `TextService(engine="gliner")` -> init succeeds unexpectedly.
- `TextService(engine="gliner").annotate_text_sync(...)` -> clear `ImportError` with install hint.
- `TextService(engine="spacy").annotate_text_sync(...)` -> clear `ImportError` with install hint.
- `TextService(engine="smart").annotate_text_sync(...)` -> silently degrades to regex output (no warning).

Compared to desired behavior:

- Regex core path: mostly works.
- Requested spaCy/GLiNER engine should fail fast at initialization: **not currently true for GLiNER/spaCy init path**.
- Smart fallback should warn when degraded: **currently silent**.

## 3.5 Async/Sync Architecture Audit

Truly async paths:

- Image/OCR stack: `ImageService` download/ocr methods, `ImageDownloader`, Donut/pytesseract async wrappers.
- Legacy `main_original` async pipelines.

Pseudo-async or sync-wrapped async:

- `services.text_service.annotate_text_async()` immediately calls sync implementation.
- `services.text_service_lean.annotate_text_async()` same pattern.

`asyncio.run()` usage:

- `datafog.client.scan_image` uses `asyncio.run(...)`.
- This can raise event-loop conflicts when called from already-running loops (Jupyter/async servers/MCP async runtime).

Event loop conflict risk:

- Present at CLI/API boundary due `asyncio.run()` in command path.
- Recommended fix: async wrappers should use `asyncio.to_thread()` or be natively awaitable at integration boundary.

## 3.6 Error Handling Audit

Search findings:

- Bare `except:` blocks: none found.
- Broad `except Exception` + silent `pass`: widespread.
- `pass` in exception blocks appears extensively in telemetry wrappers and multiple public APIs.

Assessment:

- Acceptable: telemetry fire-and-forget suppression (`telemetry.py`), as designed non-blocking path.
- Risky:
  - Swallowed exceptions in core/public API methods can hide real detection failures.
  - CLI paths catch broad exceptions and may reduce debuggability.
  - Silent fallback paths (especially smart engine) reduce observability when dependencies are missing.

## 3.7 Type Annotation Completeness

Command run:

```bash
mypy datafog/ --strict --ignore-missing-imports
```

Result:

- **228 mypy errors** across **25 files**.

Critical gaps:

- Public API modules (`datafog/__init__.py`, `datafog/client.py`, `datafog/core.py`, `datafog/main.py`) have many untyped defs and unsafe unions.
- Engine/service layer has major typing inconsistencies (`text_service.py`, `text_service_lean.py`, `main_original.py`).
- Model and anonymizer typing mismatches cause invalid call signatures and attr errors.
- CLI static check already flags a real bug: `DataFog` has no `run_ocr_pipeline`.

Raw output saved at:

- `docs/audit/03-mypy-strict.txt`

## 3.8 Telemetry Review

Implementation summary (`datafog/telemetry.py`):

- Data collected:
  - package version, python version, OS, architecture
  - installed extras probe
  - function/module names
  - coarse buckets (text length, duration)
  - error type names
- Opt-out controls:
  - `DATAFOG_NO_TELEMETRY=1`
  - `DO_NOT_TRACK=1`
- Transport:
  - daemon thread per event using `urllib.request` POST to PostHog
  - timeout set to 5 seconds
  - all network failures swallowed

Assessment:

- Opt-out mechanism is implemented correctly and tested.
- Telemetry is fire-and-forget and non-blocking by design.
- Direct PII content is not explicitly sent in telemetry calls reviewed.
- Residual risk:
  - `track_function_call(..., **kwargs)` can leak unsafe fields if future callers pass raw text accidentally.
  - Anonymous ID includes machine fingerprint hash; low PII risk but should remain documented.

## Architecture Summary

- The codebase currently has multiple overlapping runtime surfaces with inconsistent contracts.
- A single stable engine boundary is missing, which blocks clean MCP proxy integration and future Rust-core substitution.
- Optional dependency behavior and event-loop handling need explicit, deterministic semantics.
- Type coverage and error-handling hygiene are below the level needed for high-confidence API stability.
