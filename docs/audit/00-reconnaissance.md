# Phase 0 - Reconnaissance

Date: 2026-02-13  
Branch: `overhaul/audit-and-cleanup` (from `dev`)  
Environment: Windows (`powershell`), Python 3.12

## 0.1 Repository Structure Map

### Directory Tree (source + tests)

```text
datafog/
  __about__.py
  __init__.py
  __init___lean.py
  __init___original.py
  client.py
  config.py
  core.py
  exceptions.py
  main.py
  main_lean.py
  main_original.py
  telemetry.py
  models/
    __init__.py
    annotator.py
    anonymizer.py
    common.py
    spacy_nlp.py
  processing/
    __init__.py
    image_processing/
      __init__.py
      donut_processor.py
      image_downloader.py
      pytesseract_processor.py
    spark_processing/
      __init__.py
      pyspark_udfs.py
    text_processing/
      __init__.py
      gliner_annotator.py
      spacy_pii_annotator.py
      regex_annotator/
        __init__.py
        regex_annotator.py
  services/
    __init__.py
    image_service.py
    spark_service.py
    text_service.py
    text_service_lean.py
    text_service_original.py

tests/
  __init__.py
  benchmark_text_service.py
  debug_spacy_entities.py
  simple_performance_test.py
  test_anonymizer.py
  test_cli_smoke.py
  test_client.py
  test_donut_lazy_import.py
  test_gliner_annotator.py
  test_image_service.py
  test_main.py
  test_ocr_integration.py
  test_regex_annotator.py
  test_spark_integration.py
  test_telemetry.py
  test_text_service.py
  test_text_service_integration.py
  files/
    input_files/
    output_files/
```

### Source Modules

| Module                                                                  |                                                          Purpose | Lines | Has Tests? | Notes                                |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------: | ----: | ---------- | ------------------------------------ |
| `datafog/services/text_service.py`                                      |   Current main text detection service (regex/spaCy/GLiNER/smart) |   371 | Yes        | Central engine routing               |
| `datafog/client.py`                                                     |                               Typer CLI commands (`datafog ...`) |   296 | Yes        | Uses `asyncio.run()` for OCR command |
| `datafog/main.py`                                                       |                  Lean `DataFog` class (regex-only text pipeline) |   260 | Yes        | Exposed as primary `DataFog` today   |
| `datafog/services/text_service_original.py`                             |                           Legacy text service (regex/spaCy/auto) |   249 | Yes        | Heavily mock-tested                  |
| `datafog/__init__.py`                                                   |        Public exports + lazy/optional imports + convenience APIs |   237 | Yes        | Broad export surface                 |
| `datafog/telemetry.py`                                                  |                              Anonymous usage telemetry (PostHog) |   219 | Yes        | Fire-and-forget threads              |
| `datafog/main_original.py`                                              |                 Legacy full-featured `DataFog` with OCR pipeline |   213 | Yes        | Not default export now               |
| `datafog/core.py`                                                       | Lightweight functional API (`detect_pii`, `anonymize_text`, ...) |   208 | Yes        | Low coverage                         |
| `datafog/processing/text_processing/regex_annotator/regex_annotator.py` |                                 Regex patterns + span extraction |   191 | Yes        | Critical detection logic             |
| `datafog/processing/text_processing/gliner_annotator.py`                |                                  GLiNER wrapper + entity mapping |   168 | Yes        | Optional ML dependency               |
| `datafog/services/text_service_lean.py`                                 |                              Alternate lean text service variant |   158 | No         | Appears unused by runtime imports    |
| `datafog/__init___lean.py`                                              |                            Alternate lean package export variant |   154 | No         | Legacy/alternate                     |
| `datafog/main_lean.py`                                                  |                               Alternate lean main module variant |   151 | No         | Duplicate lineage                    |
| `datafog/processing/image_processing/donut_processor.py`                |                                    Donut-based OCR/understanding |   135 | Yes        | Dynamically installs deps            |
| `datafog/models/anonymizer.py`                                          |                            Redaction/replacement/hash anonymizer |   134 | Yes        | Core redaction behavior              |
| `datafog/services/image_service.py`                                     |                                  OCR/image service orchestration |   121 | Yes        | Depends on OCR extras                |
| `datafog/services/spark_service.py`                                     |                                  Spark service bootstrap wrapper |    81 | Yes        | Installs `pyspark` at runtime        |
| `datafog/processing/text_processing/spacy_pii_annotator.py`             |                                      spaCy PII annotator wrapper |    70 | Yes        | Auto-installs `en_core_web_lg`       |
| `datafog/config.py`                                                     |                             Global config + `OperationType` enum |    67 | Yes        | Pydantic settings                    |
| `datafog/models/spacy_nlp.py`                                           |                           spaCy utility annotator/model commands |    62 | Yes        | Imports `rich`                       |
| `datafog/exceptions.py`                                                 |                                         Custom exception classes |    60 | Minimal    | 0% coverage in baseline run          |
| `datafog/models/annotator.py`                                           |                               Annotation request/response models |    58 | Yes        | Well-covered                         |
| `datafog/processing/spark_processing/pyspark_udfs.py`                   |                                                Spark UDF helpers |    58 | No         | 0% coverage                          |
| `datafog/__init___original.py`                                          |                                    Alternate full export variant |    53 | No         | Legacy surface                       |
| `datafog/models/common.py`                                              |                                              Shared enums/models |    36 | Yes        | Well-covered                         |
| `datafog/processing/image_processing/image_downloader.py`               |                                      Async image download helper |    30 | Minimal    | Low direct coverage                  |
| `datafog/processing/image_processing/pytesseract_processor.py`          |                                          pytesseract OCR wrapper |    20 | Minimal    | Simple wrapper                       |
| `datafog/services/__init__.py`                                          |                                          Service package exports |    10 | Yes        | Import fallback wrappers             |
| `datafog/processing/text_processing/regex_annotator/__init__.py`        |                                        Regex annotator re-export |     6 | Yes        | Thin                                 |
| `datafog/processing/spark_processing/__init__.py`                       |                                       Spark processing re-export |     4 | No         | 0% coverage                          |
| `datafog/processing/text_processing/__init__.py`                        |                                        Text processing re-export |     2 | Yes        | Thin                                 |
| `datafog/__about__.py`                                                  |                                                 Version constant |     1 | No         | Single source of version             |
| `datafog/processing/__init__.py`                                        |                                                   Package marker |     0 | No         | Empty                                |
| `datafog/processing/image_processing/__init__.py`                       |                                                   Package marker |     0 | No         | Empty                                |
| `datafog/models/__init__.py`                                            |                                                   Package marker |     0 | No         | Empty                                |

### Test Modules

| Module                                   |                                                  Purpose | Lines | Notes                        |
| ---------------------------------------- | -------------------------------------------------------: | ----: | ---------------------------- |
| `tests/test_telemetry.py`                |                     Telemetry behavior and opt-out paths |   422 | Largest single test module   |
| `tests/test_gliner_annotator.py`         |     GLiNER behavior + integration + dependency fallbacks |   365 | Mock-heavy                   |
| `tests/test_regex_annotator.py`          |          Regex pattern correctness and regression checks |   317 | Strong structured-Pii focus  |
| `tests/test_main.py`                     |                         `DataFog` legacy + lean behavior |   290 | Mixed lean/original coverage |
| `tests/test_text_service.py`             | Legacy text service (`text_service_original`) unit tests |   278 | Mock-heavy                   |
| `tests/benchmark_text_service.py`        |                                   Performance benchmarks |   255 | Performance-focused          |
| `tests/test_client.py`                   |                CLI command unit tests using Typer runner |   188 | Mock-heavy                   |
| `tests/test_text_service_integration.py` |                         Real engine integration behavior |   137 | Includes spaCy paths         |
| `tests/test_anonymizer.py`               |                       Anonymizer modes and edge behavior |    99 | Core redaction coverage      |
| `tests/simple_performance_test.py`       |                                  Simple perf smoke tests |    97 | Returns dicts (pytest warns) |
| `tests/test_ocr_integration.py`          |                                    OCR integration tests |    95 | Donut/pytesseract dependent  |
| `tests/test_cli_smoke.py`                |                              CLI smoke integration tests |    86 | Real command flow            |
| `tests/test_spark_integration.py`        |                                  Spark integration tests |    60 | Failed in baseline (no Java) |
| `tests/test_donut_lazy_import.py`        |                               Donut lazy import behavior |    51 | Dependency handling          |
| `tests/test_image_service.py`            |                                   Image service behavior |    48 | Async/image flow             |
| `tests/debug_spacy_entities.py`          |                       Debug helper for local exploration |    15 | Not formal CI contract       |
| `tests/__init__.py`                      |                                           Package marker |     0 | Empty                        |

## 0.2 Dependency Audit

Dependency declarations are in `setup.py` (`install_requires` + `extras_require`). No `pyproject.toml` exists in this repo.

### Declared Dependencies vs Import Usage

| Dependency          | Declared As           | Imported in `datafog/`? | Notes                                |
| ------------------- | --------------------- | ----------------------- | ------------------------------------ |
| `pydantic`          | core                  | Yes                     | Core models                          |
| `pydantic-settings` | core                  | Yes                     | `datafog/config.py`                  |
| `typing-extensions` | core                  | No                      | Phantom declaration currently        |
| `spacy`             | `nlp`, `all`          | Yes                     | Used in annotators and model helpers |
| `gliner`            | `nlp-advanced`, `all` | Yes                     | Optional annotator                   |
| `torch`             | `nlp-advanced`, `all` | Yes                     | Used by Donut OCR path               |
| `transformers`      | `nlp-advanced`, `all` | Yes                     | Used by Donut OCR path               |
| `huggingface-hub`   | `nlp-advanced`, `all` | No direct import        | Transitively used by models          |
| `pytesseract`       | `ocr`, `all`          | Yes                     | OCR processor                        |
| `Pillow`            | `ocr`, `all`          | Yes (`PIL`)             | Image handling                       |
| `sentencepiece`     | `ocr`, `all`          | No direct import        | Likely transitive                    |
| `protobuf`          | `ocr`, `all`          | No direct import        | Likely transitive                    |
| `pandas`            | `distributed`, `all`  | No                      | Phantom declaration currently        |
| `numpy`             | `distributed`, `all`  | Yes                     | Donut preprocessing                  |
| `fastapi`           | `web`, `all`          | No                      | Phantom declaration currently        |
| `aiohttp`           | `web`, `all`          | Yes                     | Image download                       |
| `requests`          | `web`, `all`          | No                      | Phantom declaration currently        |
| `typer`             | `cli`, `all`          | Yes                     | CLI entrypoint                       |
| `cryptography`      | `crypto`, `all`       | No                      | Phantom declaration currently        |

### Imported But Not Declared

| Package   | Where Used                                                                                                  | Assessment                                                               |
| --------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `certifi` | `datafog/services/image_service.py`                                                                         | Imported but not declared in `setup.py`                                  |
| `rich`    | `datafog/models/spacy_nlp.py`                                                                               | Imported but not declared in `setup.py`                                  |
| `pyspark` | `datafog/services/spark_service.py`, `datafog/processing/spark_processing/pyspark_udfs.py`, telemetry probe | `distributed` extra does not declare it; runtime installs it dynamically |

### Lighter/safer alternatives worth considering

- Avoid runtime `pip install` calls in library code (`spark_service`, `donut_processor`, spaCy model download) and move to explicit install docs + clear errors.
- Remove or optionalize `rich` usage (progress bars) in core runtime paths.
- Remove `certifi` hard requirement from image path or declare it explicitly.

## 0.3 Public API Surface Inventory

### Top-level export surface (`datafog/__init__.py`)

`__all__` currently exports:

- Version: `__version__`
- Functional API: `detect`, `process`, `detect_pii`, `anonymize_text`, `scan_text`, `get_supported_entities`
- Models/types: `AnnotationResult`, `AnnotatorRequest`, `AnonymizationResult`, `Anonymizer`, `AnonymizerRequest`, `AnonymizerType`, `EntityTypes`, `RegexAnnotator`
- Class APIs: `DataFog`, `TextPIIAnnotator`, `TextService`
- CLI app: `app`
- Optional OCR/NLP/distributed: `DonutProcessor`, `PytesseractProcessor`, `ImageService`, `SpacyPIIAnnotator`, `SparkService`

Validation run in the current environment: all names in `datafog.__all__` resolved successfully.

### API inventory table

| Import Path                                  | Type      | Description                                    | Documented? | Tested?  |
| -------------------------------------------- | --------- | ---------------------------------------------- | ----------- | -------- |
| `from datafog import detect`                 | function  | Regex detection convenience API                | Yes         | Yes      |
| `from datafog import process`                | function  | Detect + optional anonymize convenience API    | Partially   | Yes      |
| `from datafog import detect_pii`             | function  | Core detection function                        | Yes         | Yes      |
| `from datafog import anonymize_text`         | function  | Core anonymization function                    | Yes         | Yes      |
| `from datafog import scan_text`              | function  | Boolean/structured scan helper                 | Yes         | Yes      |
| `from datafog import get_supported_entities` | function  | Supported entity list                          | Partial     | Indirect |
| `from datafog import DataFog`                | class     | Main class (currently lean regex in `main.py`) | Yes         | Yes      |
| `from datafog import TextPIIAnnotator`       | class     | Text annotator wrapper                         | Partial     | Partial  |
| `from datafog import TextService`            | class     | Engine-selecting text service                  | Yes         | Yes      |
| `from datafog.services import TextService`   | class     | Service import path                            | Yes         | Yes      |
| `from datafog.services import ImageService`  | class     | OCR service                                    | Partial     | Yes      |
| `from datafog.services import SparkService`  | class     | Spark service                                  | Partial     | Yes      |
| `from datafog import app`                    | Typer app | CLI command tree                               | Partial     | Yes      |

## 0.4 Entry Points / CLI Audit

### Entry point configuration

- Defined in `setup.py`:
  - `console_scripts`: `datafog=datafog.client:app [cli]`

### Command audit (`--help` + basic invocation)

All commands provide `--help` output.

| Command                      | `--help` Works? | Basic Invocation                                            | Result                                                            |
| ---------------------------- | --------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- |
| `datafog`                    | Yes             | `datafog --help`                                            | OK                                                                |
| `scan-text`                  | Yes             | `datafog scan-text "Contact john@example.com"`              | OK, but output contains false-positive empty `IP_ADDRESS` matches |
| `redact-text`                | Yes             | `datafog redact-text "Contact john@example.com"`            | OK; auto-downloads spaCy model (`en_core_web_lg`)                 |
| `replace-text`               | Yes             | `datafog replace-text ...`                                  | OK                                                                |
| `hash-text`                  | Yes             | `datafog hash-text ...`                                     | OK                                                                |
| `health`                     | Yes             | `datafog health`                                            | OK                                                                |
| `show-config`                | Yes             | `datafog show-config`                                       | OK                                                                |
| `list-models`                | Yes             | `datafog list-models --engine gliner`                       | OK                                                                |
| `list-spacy-models`          | Yes             | `datafog list-spacy-models`                                 | OK                                                                |
| `list-entities`              | Yes             | `datafog list-entities`                                     | OK                                                                |
| `show-spacy-model-directory` | Yes             | `datafog show-spacy-model-directory en_core_web_sm`         | OK; may trigger model download                                    |
| `download-model`             | Yes             | `datafog download-model en_core_web_sm --engine spacy`      | OK                                                                |
| `scan-image`                 | Yes             | `datafog scan-image tests/files/input_files/zuck-email.png` | **Fails**: `DataFog` has no `run_ocr_pipeline`                    |

Primary CLI breakage found: `scan-image` command is wired to a method that does not exist on current exported `datafog.main.DataFog`.

## 0.5 CI/CD Pipeline Audit

Workflow files found:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/benchmark.yml`

### `ci.yml`

- Triggers: push (`main`, `dev`, `feature/*`, `fix/*`, `chore/*`, `cleanup/*`), PR (`main`, `dev`)
- Python: 3.10, 3.11, 3.12 matrix
- Runs: lint (`pre-commit`), tests, wheel-size check
- Coverage: generated and uploaded to Codecov only on Python 3.10
- Gaps:
  - No coverage threshold enforcement
  - GLiNER tests are skipped in CI run command (`--ignore=tests/test_gliner_annotator.py`)
  - No explicit matrix for `core` vs `[nlp]` vs `[nlp-advanced]`
  - Accuracy corpus tests do not exist yet

### `release.yml`

- Triggers: schedule (alpha/beta cadence), manual dispatch
- Includes test gate (3.10/3.11/3.12), perf validation, publish, release tagging, cleanup
- Uses `run_tests.py` and skips GLiNER test module in gate

### `benchmark.yml`

- Triggers: push/PR (`main`, `dev`) + weekly schedule
- Runs benchmark suite and uploads artifacts
- Regression check currently intentionally disabled (baseline reset note in workflow)

## 0.6 Open Issues and PRs

### Open Issues (GitHub)

|   # | Title                            | Type          | Updated    | Stale (>30d)? | Core engine impact?          |
| --: | -------------------------------- | ------------- | ---------- | ------------- | ---------------------------- |
| 118 | Basic Usage Example Doesn't Work | Bug report    | 2026-02-09 | No            | Yes (onboarding reliability) |
|  39 | Link to documentation is stale   | Documentation | 2025-04-28 | Yes           | Low                          |

### Open PRs (GitHub)

|   # | Title                              | Kind       | Updated    | Stale (>30d)? | Merge status | Core engine impact?      |
| --: | ---------------------------------- | ---------- | ---------- | ------------- | ------------ | ------------------------ |
| 120 | bump pillow 11.2.1 -> 12.1.1       | Dependabot | 2026-02-11 | No            | CLEAN        | Low                      |
| 119 | bump cryptography 44.0.2 -> 46.0.5 | Dependabot | 2026-02-11 | No            | CLEAN        | Low                      |
| 116 | bump protobuf 6.30.2 -> 6.33.5     | Dependabot | 2026-02-01 | No            | BEHIND       | Low                      |
| 114 | bump sentencepiece 0.2.0 -> 0.2.1  | Dependabot | 2026-01-22 | No            | BEHIND       | Low                      |
| 113 | bump aiohttp 3.11.18 -> 3.13.3     | Dependabot | 2026-01-06 | Yes           | BEHIND       | Medium (web/image stack) |
| 109 | bump requests 2.32.3 -> 2.32.4     | Dependabot | 2025-06-10 | Yes           | BEHIND       | Low                      |

### Post-overhaul maintenance actions (2026-02-13)

- Closed stale documentation issue:
  - `#39` (stale docs link)
- Closed stale/dependency-behind PRs superseded by overhaul maintenance:
  - `#109` (requests bump)
  - `#113` (aiohttp bump)
- Kept active core-impact issue open with label hygiene:
  - `#118` remains open and now labeled `bug`

## Phase 0 Findings Summary

- The project currently mixes multiple parallel API generations (`*_original`, `*_lean`, current exports), creating architectural ambiguity.
- Core detection pipeline and regex annotator are substantial, but critical modules (`core.py`, `exceptions.py`, Spark helpers) are under-tested.
- Declared dependencies and actual imports are out of sync (`certifi`, `rich`, `pyspark` undeclared; several declared packages unused).
- CLI has a confirmed functional break (`scan-image` path).
- CI covers multi-Python but not multi-extras configuration and does not enforce coverage thresholds.
