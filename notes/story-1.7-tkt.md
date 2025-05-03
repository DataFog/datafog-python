**Story 1.7: Integration tests (no mocks)**

- [x] Run pytest with `-m "integration"` to run Spark in local mode.
- [x] Smoke test the CLI with a tmp file.
- [x] OCR path behind `PYTEST_DONUT=yes` flag.

**Status: COMPLETED**

## Summary

This story focused on implementing robust integration tests for the DataFog project. We successfully:

1. Added integration test markers and configurations to run Spark in local mode
2. Created smoke tests for the CLI using temporary files to verify functionality
3. Implemented conditional OCR testing with the PYTEST_DONUT flag to control when real OCR is used

All tests can now be run with `pytest -m "integration"` and the OCR tests can be run with real OCR functionality by setting `PYTEST_DONUT=yes`.

## Implementation Notes

### Spark Integration Tests

1. Added integration marker to pytest configuration in tox.ini
2. Created test_spark_integration.py with tests for SparkService in local mode
3. Updated SparkService to support local mode for integration testing
4. Added integration markers to existing text_service_integration.py tests
5. Added a dedicated tox environment for running integration tests

To run the integration tests:

```bash
tox -e integration
```

Or directly with pytest:

```bash
pytest -m "integration"
```

### CLI Smoke Tests

1. Created test_cli_smoke.py with integration tests for the CLI commands
2. Implemented tests that use temporary files to test CLI functionality
3. Added tests for key CLI commands: health, show-config, scan-text, redact-text, replace-text, and list-entities
4. Used the typer.testing.CliRunner to invoke CLI commands programmatically
5. Applied the integration marker to all CLI smoke tests

The CLI smoke tests verify that:

- Basic CLI commands execute successfully
- Text processing commands correctly handle PII in text files
- Configuration and entity listing commands return expected information

### OCR Path Behind PYTEST_DONUT=yes Flag

1. Updated DonutProcessor to check for the PYTEST_DONUT environment variable
2. Modified ImageService to respect the PYTEST_DONUT flag when initializing OCR processors
3. Created test_ocr_integration.py with tests that demonstrate both mock and real OCR functionality
4. Implemented conditional logic to use mock OCR by default in tests, but real OCR when PYTEST_DONUT=yes
5. Added proper logging to indicate when mock vs. real OCR is being used

To run tests with the real OCR implementation:

```bash
PYTEST_DONUT=yes pytest -m "integration" tests/test_ocr_integration.py
```

Without the flag, tests will use mock OCR responses to avoid dependencies on torch/transformers:

```bash
pytest -m "integration" tests/test_ocr_integration.py
```
