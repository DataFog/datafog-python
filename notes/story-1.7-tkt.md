**Story 1.7: Integration tests (no mocks)**

- [x] Run pytest with `-m "integration"` to run Spark in local mode.
- [x] Smoke test the CLI with a tmp file.
- [ ] OCR path behind `PYTEST_DONUT=yes` flag.

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
