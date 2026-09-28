# Migrating incrementally with DataFog 4.9

4.9 is a bridge to the Rust-backed 5.0 API. The default Python detector, existing
imports, result objects, and redaction strategies continue to work. The optional
Rust backend and native API preview are experimental and explicitly selected.

## Opt into Rust detection

```bash
pip install "datafog[rust]"
```

The extra pins the tested `datafog-core==0.3.1` wheel. The base package needs no
Rust installation or native module. The existing `all` extra retains its legacy
dependency set; request `rust` explicitly, or use `datafog[all,rust]`.

```python
import datafog

result = datafog.scan("Contact alice@example.com", backend="rust")
assert result.entities[0].type == "EMAIL"

result = datafog.redact("Contact alice@example.com", backend="rust")
assert result.redacted_text == "Contact [EMAIL_1]"
assert result.mapping == {"[EMAIL_1]": "alice@example.com"}
```

`backend` is keyword-only and defaults to `python`. Only `engine="regex"` supports
the Rust backend in 4.9. Low-level `datafog.engine.scan` and `scan_and_redact`
default to `smart`, so pass `engine="regex"` explicitly there. Missing native
dependencies and unsupported combinations raise errors; there is no automatic
fallback to Python. Native scanning failures propagate instead of becoming empty
results.

The legacy adapter converts Core code-point offsets to Python indices and keeps
legacy `regex` provenance and confidence `1.0` as compatibility values, not native
probability estimates. It retains Python aliases, full-match allowlists (including
Python regex syntax), overlap selection, and transformations. Supplying explicit
entities to `redact` performs no detection and requires no native dependency.

`sanitize`, `scan_prompt`, and `filter_output` forward the backend keyword. The
`DataFog` class, `TextService`, legacy convenience APIs, CLI, guardrail objects,
application adapters, and ML composition retain their existing detection paths.
Installing the extra alone does not change any of those paths.

## Existing and new result schemas

The compatibility namespace provides the scan/redact API explicitly:

```python
from datafog.compat.v4 import Entity, ScanResult, RedactResult, scan, redact
```

Top-level scan/redact delegate to this facade. Result classes retain their
existing identity; their fields and positional calling conventions are preserved.
The compatibility namespace excludes `detect` and `process`.

The native preview exports the actual Core objects, including structured scanning,
transformations, and provider-backed operations:

```python
from datafog.v5 import Finding, scan, scan_and_transform

findings = scan("Contact alice@example.com")
assert isinstance(findings[0], Finding)
assert findings[0].entity_type == "EMAIL"

result = scan_and_transform(
    "Contact alice@example.com",
    {"transform": {"default": {"strategy": "redact"}}},
)
assert result.text == "Contact [EMAIL]"
```

Importing `datafog` or the preview namespace alone does not import Core. Accessing
preview functions/types requires the Rust extra. Preview names are reexports,
not a second implementation or a legacy-schema adapter.

| Existing Python API                        | Core preview                                                   |
| ------------------------------------------ | -------------------------------------------------------------- |
| `ScanResult.entities`                      | `list[Finding]`                                                |
| `Entity.type`, `text`, `start`, `end`      | `entity_type`, `matched_text`, explicit byte/code-point ranges |
| `RedactResult.redacted_text`               | `TransformResult.text`                                         |
| Numbered type tokens and plaintext mapping | Unnumbered redaction placeholders and transformation records   |
| Legacy `hash` and numbered `pseudonymize`  | Explicit keyed/provider-backed Core strategies                 |

Legacy `token` is not Core `tokenize`. Do not mechanically rename strategies or
assume that the two schemas and provider requirements are interchangeable.

## Known detection differences

Core 0.3.1 does not implement the seven German detectors. The legacy Rust adapter
rejects German locales and `DE_*` selections, directing callers to Python.
The raw native preview retains Core's own API: its accepted locale configuration
does not imply German detector coverage. Continue using Python for those workloads.

The frozen 111-case baseline yields the following Rust-backend comparison:

| Outcome                      | Cases | Interpretation                                                            |
| ---------------------------- | ----: | ------------------------------------------------------------------------- |
| Exact match                  |    61 | Same observable result on these inputs                                    |
| Reviewed detector difference |     2 | Invalid-checksum card and alphanumeric-embedded SSN are rejected by Core  |
| Explicitly unsupported       |    17 | German requests fail rather than silently lose coverage                   |
| Outside backend scope        |    31 | Signatures, explicit-span transformations, legacy/service/guardrail paths |

These counts describe this finite synthetic corpus, not universal detection
equivalence or precision/recall. See `tests/contracts/rust-0.3.1.json` for exact
reviewed outcomes and reasons. Each applicable case is asserted independently;
unknown differences fail CI. Generate the full per-case report with:

```bash
python -m tests.rust_contract --output /tmp/rust-parity.json
```

The published `tests/contracts/4.8.1.json` remains unchanged. The 4.9 checker
permits only four added keyword-only backend parameters and the explicitly
revised detect/process warning messages; all other legacy observations remain
exact comparisons. The standalone oracle runner still checks exact 4.8.1 behavior
and should be used with the released 4.8.1 wheel, not the 4.9 checkout.

## Retirement schedule

| Surface                                  | 4.9                                      | 5.0 plan                                                                   |
| ---------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------- |
| `detect()` / `process()`                 | Still work; updated `FutureWarning`      | Remove                                                                     |
| OCR / Donut / Tesseract / image services | Still work; use-time deprecation notices | Remove supported OCR surfaces and extras                                   |
| Spark / distributed processing           | Still work; use-time deprecation notices | Remove supported Spark surfaces and extras                                 |
| Legacy scan/redact facade                | Available at top level and `compat.v4`   | Native schema becomes primary; compatibility lifetime to be set separately |
| spaCy / GLiNER                           | Unchanged                                | No removal decision in this increment                                      |

**The earlier promise to retain `detect` and `process` throughout 5.x is revised.**
They are now scheduled for removal in 5.0. Use `scan` or `redact` in 4.9 and evaluate
the native preview before upgrading to 5.0. `process(anonymize=True)` used older
placeholder/hash semantics; migrating to `redact` can intentionally change output.

Users needing OCR/Spark can remain on the final 4.x release. No successor package
or indefinite support commitment is introduced here. Deprecation notices do not
trigger downloads or import heavy dependencies during ordinary text imports.

## Verification and performance

Run the contract/backend suites with and without the Rust extra. CI also builds
and installs a wheel, then runs an isolated-interpreter smoke test on Linux,
macOS and Windows; it does not rely solely on imports from the checkout.

```bash
python -m pytest tests/test_contract_481.py tests/test_rust_backend.py \
  tests/test_api_bridge_49.py tests/test_rust_contract.py -q
python benchmarks/compare_detection_backends.py --output /tmp/backend-timings.json
```

The benchmark measures public calls, including native/Python conversion,
redaction, and fresh-process startup on short, mixed, and roughly 1 MB sparse
synthetic text. It reports entity counts alongside timings. No general speedup
claim is made from a single machine or from cases with different outputs.

A local CPython 3.12 macOS ARM64 reference run is recorded in
`benchmarks/results-4.9.json`. Median scan latency was 19.74 versus 2.30 microseconds
for the short payload, 39.50 versus 7.58 microseconds for mixed PII, and 121.91
versus 5.33 milliseconds for the large sparse payload (Python versus Rust).
Fresh-process import plus first scan was approximately 81 milliseconds for both.
These are local measurements, not release performance guarantees.
