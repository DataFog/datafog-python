# ChangeLog

## [2026-07-02]

### `datafog-python` [4.5.0]

#### Behavior Changes Since 4.4.0

- Agent guardrail helpers (`sanitize`, `scan_prompt`, `filter_output`,
  `create_guardrail`, and the `Guardrail` class) now default to
  `engine="regex"` instead of `engine="smart"`, matching the top-level
  `scan`/`redact`/`protect` defaults. This keeps the core install from
  probing optional NLP dependencies, but means NER-backed entities
  (PERSON, ORGANIZATION, LOCATION) are no longer detected by these
  helpers unless requested. **Migration:** pass `engine="smart"` to
  restore the 4.4.0 behavior (requires `datafog[nlp]` or
  `datafog[nlp-advanced]`).
- `DataFog.detect()` / `DataFog.scan_text()` result dictionaries now
  contain keys only for the labels active under the configured locales:
  the seven base labels by default, plus the `DE_*` labels when
  constructed with `locales=["de"]`.
- Supported Python versions are `>=3.10,<3.14`. Python 3.14 is not yet
  certified and is intentionally excluded from this release.

#### Release Thesis

- Frames 4.5.0 as a focused, lightweight text PII screening release rather
  than a v5 package overhaul.
- Keeps the first path centered on core install, regex scanning/redaction,
  CLI text commands, and agent-oriented guardrail helpers.
- Defers dedicated Sentry, OpenTelemetry, logging-framework, and cloud DLP
  middleware adapters to v5 planning.

#### Core Text PII Screening

- Clarifies the live top-level APIs: `scan`, `redact`, `protect`,
  `scan_prompt`, `filter_output`, `sanitize`, and guardrail helpers.
- Documents the current module map so users and contributors can distinguish
  live 4.5 modules from historical compatibility and audit artifacts.
- Preserves backward-compatible `DataFog` and `TextService` entry points.

#### German Structured PII

- Adds regex-only German structured PII support without adding core
  dependencies.
- All German identifiers are locale-gated: they activate only through
  `locales=["de"]` or explicit entity selection. This covers German VAT
  IDs, IBANs, tax IDs, pension insurance numbers, postal codes, passport
  numbers, and residence permit numbers. Default (no-locale) detection
  behavior is unchanged from 4.4.0.
- When German locale support is active, overlapping matches (e.g. the
  nine-digit run inside a VAT ID also matching the generic SSN pattern)
  are resolved by engine-level span-overlap suppression in favor of the
  more specific German label.

#### Optional Profiles And Python 3.13

- Certifies Python 3.13 support for the core SDK, CLI, `nlp`, `nlp-advanced`,
  and `ocr` install profiles.
- Adds CI coverage for Python 3.13 `nlp` and `nlp-advanced` test profiles plus
  3.13 smoke checks for `nlp`, `nlp-advanced`, and `ocr`.
- Documents Donut OCR as requiring a local model before runtime use.
- Leaves `distributed` and `all` outside the new Python 3.13 certification
  claim for 4.5.0.

#### Optional OCR And Spark Surfaces

- Documents OCR and Spark as supported optional surfaces, not deprecated
  features and not the main 4.5 adoption path.
- Keeps local OCR behind `datafog[ocr]`, URL image inputs behind
  `datafog[web,ocr]`, Donut behind `datafog[nlp-advanced,ocr]`, and Spark
  behind `datafog[distributed]`.

#### Telemetry And Privacy

- Documents telemetry behavior without changing defaults.
- Telemetry remains disabled unless `DATAFOG_TELEMETRY=1` is set.
- `DATAFOG_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` continue to force telemetry
  off for tests, CI, and privacy-sensitive environments.

#### Release Readiness

- Adds a 4.5 release-readiness checklist covering docs build, formatting,
  core no-network checks, install-profile smoke checks, German regex tests,
  broad non-slow tests, package build checks, and final CI status.
- Clarifies the version alignment path: development prereleases publish as
  `4.5.0aN`/`4.5.0bN` from `dev`, and the stable release publishes as
  `4.5.0` via the Release workflow's `stable` dispatch from `main`.

## [2026-02-13]

### `datafog-python` [4.3.0]

#### Audit and Architecture

- Added a new internal engine boundary in `datafog/engine.py`:
  - `scan()`
  - `redact()`
  - `scan_and_redact()`
  - dataclasses: `Entity`, `ScanResult`, `RedactResult`
- Updated core compatibility layers (`datafog.core`, `datafog.main`, CLI paths) to delegate through the engine interface.
- Added `EngineNotAvailable` error for clear optional dependency failures.
- Improved smart engine behavior for graceful fallback when optional NLP dependencies are unavailable.

#### Accuracy and Testing

- Added a corpus-driven detection accuracy suite:
  - `tests/corpus/structured_pii.json`
  - `tests/corpus/unstructured_pii.json`
  - `tests/corpus/mixed_pii.json`
  - `tests/corpus/negative_cases.json`
  - `tests/corpus/edge_cases.json`
  - `tests/test_detection_accuracy.py`
- Improved regex patterns for email, date/year handling, SSN boundaries, and strict IPv4 matching.
- Added explicit `xfail` markers for known model limitations in select smart/NER corpus cases.
- Added engine API tests in `tests/test_engine_api.py`.
- Added agent API tests in `tests/test_agent_api.py`.
- Updated Spark integration tests to skip cleanly when Java is not available.

#### Agent API

- Added `datafog/agent.py` with:
  - `sanitize()`
  - `scan_prompt()`
  - `filter_output()`
  - `create_guardrail()`
  - `Guardrail` and `GuardrailWatch`
- Exported agent-oriented API from top-level `datafog` package.

#### CI/CD and Documentation

- Updated GitHub Actions CI matrix to test Python `3.10`, `3.11`, and `3.12` across `core`, `nlp`, and `nlp-advanced` profiles.
- Added coverage enforcement thresholds in CI (line and branch).
- Added a dedicated corpus accuracy run in CI.
- Rewrote `README.md` with validated, copy-pasteable examples and a dedicated LLM guardrails section.
- Added/updated audit reports under `docs/audit/`.

## [2025-05-29]

### `datafog-python` [4.2.0]

#### Major Features

- **GLiNER Integration**: Added modern Named Entity Recognition engine with GLiNER (Generalist Model for NER)
  - New `gliner` engine option in TextService providing 32x performance improvement over spaCy
  - PII-specialized model support (`urchade/gliner_multi_pii-v1`) for enhanced accuracy
  - Custom entity type configuration for domain-specific detection
  - Automatic model downloading and caching functionality

- **Smart Cascading Engine**: Introduced intelligent multi-engine approach
  - New `smart` engine that progressively tries regex → GLiNER → spaCy
  - Configurable stopping criteria based on entity count thresholds
  - Optimized for best accuracy/performance balance (60x average speedup)

- **Enhanced CLI Model Management**: Extended command-line interface
  - `--engine` flag support for `download-model` and `list-models` commands
  - GLiNER model discovery and management capabilities
  - Unified model management across spaCy and GLiNER engines

#### Architecture Improvements

- **Optional Dependencies**: Added new `nlp-advanced` extra for GLiNER dependencies
  - `pip install datafog[nlp-advanced]` for GLiNER + PyTorch + Transformers
  - Maintained lightweight core architecture (<2MB)
  - Graceful degradation when GLiNER dependencies unavailable

- **Engine Ecosystem**: Expanded from 3 to 5 annotation engines
  - `regex`: 190x faster, structured PII detection (core only)
  - `gliner`: 32x faster, modern NER with custom entities
  - `spacy`: Traditional NLP, comprehensive entity recognition
  - `smart`: Cascading approach for optimal accuracy/speed
  - `auto`: Legacy regex→spaCy fallback

#### Performance & Quality

- **Validated Performance**: Comprehensive benchmarking across all engines
  - GLiNER: 32x faster than spaCy with superior NER accuracy
  - Smart cascading: 60x average speedup with highest accuracy scores
  - Regex: Maintained 190x performance advantage

- **Comprehensive Testing**: Added 19 new test cases for GLiNER integration
  - Full coverage of GLiNER annotator functionality
  - Graceful degradation testing for missing dependencies
  - Smart cascading logic validation
  - Cross-engine integration testing

#### Documentation & Developer Experience

- **Updated Documentation**: Comprehensive guides and examples
  - README performance comparison table with all 5 engines
  - Engine selection guidance with use case recommendations
  - GLiNER model management and CLI usage examples
  - Installation options for different dependency combinations

- **Developer Guide**: Streamlined development documentation
  - Updated architecture overview with GLiNER integration
  - Performance requirements and testing strategies
  - Common development patterns and best practices

#### Breaking Changes

- **Engine Options**: New engine types added to TextService
  - Existing code using `engine="auto"` continues to work unchanged
  - New engines `gliner` and `smart` require `[nlp-advanced]` extra

#### Dependencies

- **New Optional Dependencies** (nlp-advanced extra):
  - `gliner>=0.2.5`
  - `torch>=2.1.0,<2.7`
  - `transformers>=4.20.0`
  - `huggingface-hub>=0.16.0`

#### Migration Guide

For users upgrading from v4.1.1:
- All existing functionality remains unchanged
- To use GLiNER: `pip install datafog[nlp-advanced]`
- Smart cascading: `TextService(engine="smart")` for best balance
- CLI: Use `--engine gliner` flag for GLiNER model management

## [2025-05-05]

### `datafog-python` [4.1.1]

- Added engine selection functionality to TextService class, allowing users to choose between 'regex', 'spacy', or 'auto' annotation engines
- Enhanced TextService with intelligent fallback mechanism in 'auto' mode that tries regex first and falls back to spaCy if no entities are found
- Added comprehensive integration tests for the new engine selection feature
- Implemented performance benchmarks showing regex engine is ~123x faster than spaCy
- Added CI pipeline for continuous performance monitoring with regression detection
- Added wheel-size gate (< 8 MB) to CI pipeline
- Added 'When do I need spaCy?' guidance to documentation
- Created scripts for running benchmarks locally and comparing results
- Improved documentation with performance metrics and engine selection guidance
- Extended .gitignore to better handle build artifacts and development files
- Added GitHub Actions workflows for testing, linting, and benchmarking
- Pinned all dependency versions in requirements.txt and requirements-dev.txt for reproducible builds
- Added mypy type checking to CI pipeline
- Added ruff linting to development dependencies
- Finalized stable release, no breaking changes from 4.1.0b5

## [2024-03-25]

### `datafog-python` [4.0.0]

- Added datafog-python/examples/uploading-file-types.ipynb to show JSON uploading example (#16)
- Added datafog-python/tests/regex_issue.py to show issue with regex recognizer creation
- Moved versioning to separate invocable function in setup.py
