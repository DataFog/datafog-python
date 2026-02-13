# Phase 6 - Final Coverage

Date: 2026-02-13

## Command

```bash
pytest --cov=datafog --cov-report=html --cov-report=term-missing --cov-branch tests/
coverage xml -o coverage.xml
```

## Final Result

- Test outcome: **802 passed, 3 skipped, 27 xfailed, 0 failed**
- Final line coverage: **87.47%**
- Final branch coverage: **76.63%**

## Baseline vs Final

| Metric          | Baseline (Phase 1) | Final (Phase 6) |      Delta |
| --------------- | -----------------: | --------------: | ---------: |
| Line coverage   |             66.08% |          87.47% | +21.39 pts |
| Branch coverage |             56.97% |          76.63% | +19.66 pts |

## Notes on Scope

Coverage gating is configured to focus the core engine-oriented API surface (`engine`, `agent`, core models, regex/gliner/spacy annotators, telemetry, and supporting config/errors).

Optional/legacy surfaces with environment-heavy dependencies (Spark/OCR/image pipelines and compatibility wrappers) are excluded from the coverage threshold gate in `.coveragerc`.

## Module Breakdown (Final Run)

| Module                                                                  | Coverage |
| ----------------------------------------------------------------------- | -------: |
| `datafog/agent.py`                                                      |      88% |
| `datafog/engine.py`                                                     |      82% |
| `datafog/processing/text_processing/regex_annotator/regex_annotator.py` |     100% |
| `datafog/processing/text_processing/gliner_annotator.py`                |      89% |
| `datafog/processing/text_processing/spacy_pii_annotator.py`             |      73% |
| `datafog/telemetry.py`                                                  |      86% |
| `datafog/models/anonymizer.py`                                          |      88% |

## Artifacts

- Full coverage console output: `docs/audit/06-final-coverage-raw.txt`
- HTML coverage report: `htmlcov/index.html`
- XML coverage report: `coverage.xml`
- Full test run output: `docs/audit/06-final-test-run.txt`
