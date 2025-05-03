# ChangeLog

## [2025-05-02]

### `datafog-python` [4.1.0]

- Added engine selection functionality to TextService class, allowing users to choose between 'regex', 'spacy', or 'auto' annotation engines
- Enhanced TextService with intelligent fallback mechanism in 'auto' mode that tries regex first and falls back to spaCy if no entities are found
- Added comprehensive integration tests for the new engine selection feature
- Implemented performance benchmarks showing regex engine is ~123x faster than spaCy
- Added CI pipeline for continuous performance monitoring with regression detection
- Added wheel-size gate (< 8 MB) to CI pipeline
- Added 'When do I need spaCy?' guidance to documentation
- Created scripts for running benchmarks locally and comparing results
- Improved documentation with performance metrics and engine selection guidance

## [2024-03-25]

### `datafog-python` [4.0.0]

- Added datafog-python/examples/uploading-file-types.ipynb to show JSON uploading example (#16)
- Added datafog-python/tests/regex_issue.py to show issue with regex recognizer creation
- Moved versioning to separate invocable function in setup.py
