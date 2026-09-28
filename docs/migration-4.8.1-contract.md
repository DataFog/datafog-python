# DataFog 4.8.1 compatibility contract

This is the release baseline for migrating the Python structured-text API to
DataFog Core. It freezes **111 black-box observations from the published 4.8.1
wheel**, not expectations generated from the development checkout. It does not
claim that every observed detector behavior is desirable or that Core already
matches this contract.

## Source and scope

The source is [datafog 4.8.1 on PyPI](https://pypi.org/project/datafog/4.8.1/),
uploaded July 28, 2026. The fixture records the wheel URL, filename, SHA-256,
capture interpreter, and dependency versions. The wheel SHA-256 is:

```text
d91cfb6d93568c9d073ca3ec93b492d29195f44828584556bd7bc443d3347040
```

- `tests/contracts/4.8.1.json`: synthetic inputs and frozen results, warnings,
  exceptions, selected function signatures, and dataclass field names.
- `tests/contract_481.py`: shared black-box runner for installed distributions
  and the checkout. No detector or replacement algorithms are duplicated here.
- `tests/test_contract_481.py`: one independently identified pytest case per
  observation, automatically included in the existing CI `pytest tests/` runs.
- `scripts/capture_481_contract.py`: verifies the wheel digest and installed
  package bytes before producing a separate candidate baseline for review.

Covered surfaces are top-level `scan`, `redact`, the engine's explicit-span
redaction and scan/redact helper, agent convenience functions, guardrail
filter/block behavior, legacy `detect`/`process` and core convenience functions,
and synchronous regex `TextService` annotation/batching. Signatures cover the
principal scan/redact/guardrail entry points and result constructors.

This is the **structured synchronous text migration contract**, not a complete
contract for every package export. ML inference, smart/auto fallback behavior,
OCR, Spark, async/concurrency behavior, CLI output/exit codes, `DataFog` class
workflows, and Claude/LiteLLM adapters require their existing dedicated suites
and separate migration acceptance checks. Model quality and performance are
not inferred from these snapshots. No models or external services are needed.

## Compatibility requirements

| Concern               | 4.8.1 behavior to preserve at existing Python entry points                                                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Results               | `ScanResult(entities, text, engine_used)`; `Entity(type, text, start, end, confidence, engine)`; `RedactResult(redacted_text, mapping, entities)`                                                                   |
| Defaults              | Top-level scan/redact and agent helpers use regex; the engine scan/helper defaults remain `smart` in the signature snapshot                                                                                         |
| Offsets               | Zero-based, end-exclusive Python string indices. Emoji, modifiers, combining characters, CJK, and CRLF are preserved without normalization. Use Core code-point ranges, never byte ranges                           |
| Findings              | Ordered findings with original matched text, numeric regex confidence `1.0`, and `regex` provenance; repeated occurrences retain separate spans                                                                     |
| Selection             | Canonical labels and aliases such as `EMAIL_ADDRESS`, `US_SSN`, `PHONE_NUMBER`, `DOB`, and `ZIP`; case/whitespace normalization. Empty selection means no restriction; an unknown-only selection yields no findings |
| Locales               | Seven German entity families enabled by `de`/locale aliases or explicit entity selection; unsupported locale raises `ValueError`                                                                                    |
| Allowlists            | Case-sensitive exact values or full-match Python regexes; validation occurs even for empty input. Lookahead is included because moving to Rust regex syntax can change accepted patterns                            |
| Explicit spans        | Unsorted input is accepted; duplicate/overlapping spans are suppressed. Longest wins, then entity priority, confidence, and deterministic position/type ordering; adjacent spans remain distinct                    |
| `token`               | Per-type numbering in document order, including repeated values: `[EMAIL_1]`, `[EMAIL_2]`; counters restart per call                                                                                                |
| `mask`                | One `*` per Python character; mappings use numbered keys such as `[EMAIL_MASK_1]` so equal-length values do not collide                                                                                             |
| Engine `hash`         | SHA-256 of the source value, truncated to 12 hex digits, inside a typed placeholder                                                                                                                                 |
| Engine `pseudonymize` | Per-call numbered placeholders reused for repeated `(type, value)` pairs; no key provider and no cross-call linkage guarantee                                                                                       |
| Mappings              | Replacement keys map to original plaintext; returned entities are the applied, surviving spans. Preserve only on compatibility APIs, without adding plaintext to Core transformation records                        |
| Presets               | `default`/`llm`, `mask`, `hash`, `replace`, and `pseudonymize` retain their existing mappings                                                                                                                       |
| Validation            | Exception classes and observed messages are captured, including rejected strategy/preset names and allowlists combined with explicit spans                                                                          |
| Legacy functions      | `detect` and `process` emit `FutureWarning` promising shims through 5.x. `process(anonymize=True)` has its own older placeholders and 8-digit MD5 hash output; it is not equivalent to engine redaction             |
| Service API           | Regex `TextService` returns a label-to-values dictionary including empty buckets and legacy `DOB`/`ZIP` labels; the modern scan facade returns canonical entities                                                   |

The JSON is the exact executable evidence for the selected inputs. This table
explains the intended compatibility policy; finite examples are not proof of
complete detector coverage. In particular, legacy `token` must not silently
become Core's provider-backed `tokenize`, and legacy `pseudonymize` must not
silently acquire key-provider requirements.

## Observations requiring migration review

Cases marked `review-required` remain checked so a change cannot pass unnoticed.
They are **not instructions to reimplement bugs in Rust**.

| Case IDs                                                                          | Observed behavior                                                                                              | Proposed treatment                                                                        |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `scan-observation-invalid-card`                                                   | Card-shaped input with an invalid checksum is detected                                                         | Review as a detector-quality change; document any intentional difference                  |
| `scan-observation-boundary`, `scan-observation-ambiguous-number`                  | Embedded SSN-like values and arbitrary ten-digit numbers are detected                                          | Evaluate precision/recall before deciding parity                                          |
| `locale-default-DE_VAT_ID`, `locale-default-DE_TAX_ID`, `locale-negative-context` | German-looking numbers can still match generic SSN/PHONE detectors without a German finding                    | Preserve opt-in locale semantics; review generic detector differences separately          |
| `explicit-invalid-bounds`                                                         | Invalid bounds are silently discarded                                                                          | Consider explicit validation in the new API; retain or explicitly migrate legacy behavior |
| `explicit-mismatched-text`                                                        | Replacement uses the source slice even when `Entity.text` disagrees; returned entity retains the supplied text | Prefer Core validation for the new API; explicitly decide compatibility behavior          |
| `process-invalid`                                                                 | Unknown legacy anonymization method produces an unnumbered type placeholder                                    | Preserve in the promised shim or announce an intentional change                           |

For any future mismatch, record the case ID, old/new result, classification
(regression, intentional improvement, or deliberate breaking change), rationale,
and targeted test in the migration PR. Do not regenerate the 4.8.1 fixture from
the implementation being migrated. If approved deviations become necessary,
record them separately by case ID with rationale; never blanket-skip this suite.

## Run and reproduce

Run the checkout contract with the normal development environment:

```bash
python -m pytest tests/test_contract_481.py -q
```

To independently check the published wheel, run from the repository root using
an isolated Python 3.12 environment. Substitute an unused temporary directory:

```bash
python3.12 -m venv /tmp/datafog-481-oracle
/tmp/datafog-481-oracle/bin/python -m pip download --no-deps --only-binary=:all: \
  --index-url https://pypi.org/simple datafog==4.8.1 -d /tmp/datafog-481-oracle
/tmp/datafog-481-oracle/bin/python -m pip install \
  -r tests/contracts/requirements-4.8.1.txt \
  /tmp/datafog-481-oracle/datafog-4.8.1-py3-none-any.whl
/tmp/datafog-481-oracle/bin/python -I tests/contract_481.py
/tmp/datafog-481-oracle/bin/python -I scripts/capture_481_contract.py \
  --wheel /tmp/datafog-481-oracle/datafog-4.8.1-py3-none-any.whl \
  --output /tmp/datafog-481-oracle/candidate.json
```

The isolated flag excludes the checkout and `PYTHONPATH` from imports. Capture
checks version, wheel SHA-256, installed file bytes, and import location. It
refuses to overwrite the committed baseline or an existing candidate file.
Compare candidate cases to the committed cases; interpreter/dependency metadata
may differ on another environment. Routine CI is offline with respect to the
oracle: it reads committed expectations and never downloads or regenerates them.
The runner disables DataFog telemetry for its synthetic inputs.

When introducing the Rust adapter, run these same cases through the existing
Python facade with that backend selected. Direct Core result objects have a
different API and should retain their own cross-runtime conformance suite.
