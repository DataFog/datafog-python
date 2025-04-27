# ChangeLog

## [2025-04-27]

### Benchmarking

- Added benchmarking scripts (`scripts/bench_sdk.py`, `scripts/bench_cli.sh`) to compare the performance of PII redaction using the Python SDK versus the CLI.
- Created a sample OpenTelemetry log file (`scripts/sample_otel_log.json`) containing 51 string fields for testing.
- **Methodology:**
  - **SDK Benchmark (`bench_sdk.py`):** Reads the entire JSON file, extracts all string values, and times a single call to the SDK's `annotate_text` and `anonymize` functions to process all extracted strings together. The measurement was repeated 10 times, and the fastest run was reported.
  - **CLI Benchmark (`bench_cli.sh`):** Uses `jq` to extract all string values from the JSON file and pipes them via `xargs` to the `datafog redact-text` command. This results in a separate invocation of the `datafog` CLI process for _each_ extracted string. The total time for processing all strings in this manner was measured over 5 loops.
- **Results:**
  - **SDK:** Demonstrated significantly faster performance due to single process initialization and batch processing.
    - Fastest time to process all 51 strings from `sample_otel_log.json`: **~1.15 seconds**.
  - **CLI:** Showed much slower performance, primarily attributed to the overhead of starting a new `datafog` process and loading models for each of the 51 strings individually.
    - Time per loop (processing all 51 strings via individual CLI calls): **~41-42 seconds** (based on initial runs).

## [2024-03-25]

### `datafog-python` [2.3.2]

- Added datafog-python/examples/uploading-file-types.ipynb to show JSON uploading example (#16)
- Added datafog-python/tests/regex_issue.py to show issue with regex recognizer creation
- Moved versioning to separate invocable function in setup.py
