# November 2026 review remediation

This candidate addresses the review of DataFog 4.11.0 and Core 1.4.0. The
review's suggested fixes were assessed against the local implementations;
regression tests cover the implemented behavior.

## Observable behavior

All engine modes and legacy scanning APIs share the structured scan boundary.
Optional NER adds spans with its own character offsets. TextService scans the
whole document; `text_chunk_length` remains validated for compatibility.
Unsupported labels, invalid ranges and invalid locales fail explicitly. Source
code-point offsets remain stable when lone surrogate characters are replaced
for native transport. `get_supported_entities()` reports supported labels,
including opt-in ones, rather than only currently active default labels.

The `create_guardrail` decorator supports sync and async functions returning
strings. Non-string results raise TypeError; they cannot silently bypass the
filter. Apply a guardrail directly to the text fields of structured results.

LiteLLM scans messages, nested tool/function arguments, prompt and input fields.
Image and binary parts are retained without OCR. Tokens are assigned per request
or response and repeated values reuse their token. Streamed response text and
tool arguments are buffered until completion, then scanned before any chunk is
emitted. This adds completion latency. Exceeding eight million text characters
or 100,000 chunks rejects the stream. Engine failures follow the explicit
`fail_policy`; deployments requiring protected egress should select `closed`.
The Claude Code hook requests review or denies oversized PreToolUse inputs;
nonblocking events receive an explicit incomplete-scan notice. Unexpected hook
failures retain the documented fail-open contract and log exception types only.

`hash_type` selects md5, sha256 or sha3_256 on the CLI and legacy model APIs.
The engine also accepts fixed-length algorithms provided by hashlib. Existing
plain-hash marker formats remain compatible: engine, class facade and CLI
markers use 12 hex characters with SHA256 as their default; deprecated top-level
`process` uses eight hex characters and retains its MD5 default. Its explicit
`hash_type` option uses that same legacy width. The legacy Anonymizer model keeps
its existing full plain digests. Explicit keyed hashes use the full HMAC digest;
an omitted algorithm selects SHA256 for this new keyed mode.
Plain deterministic hashes are pseudonymization: SSNs, phones and
other guessable inputs can be enumerated. Use `hash_key` (at least 32 random
bytes) for keyed HMAC and keep the key outside logs and source control:

```python
import secrets
import datafog
key = secrets.token_bytes(32)  # store securely to reproduce pseudonyms
result = datafog.redact("mail jane@example.com", strategy="hash", hash_key=key)
```

## Release sequence and qualification

The Python 4.12.0 candidate declares `datafog-core~=1.5.0` in its base
requirements and `rust` extra. Its reviewed native contract is
[`tests/contracts/rust-1.5.0.json`](../tests/contracts/rust-1.5.0.json).
Core 1.5.0 is prepared separately as a minor release with the detector and
transformation safety fixes from the review, including bounded mask reveal
and complete scanner coverage for automatic overlap handling. Public APIs
remain available and both packages continue to use capability contract 1.

This branch prepares the dependent package without publishing either project.
Its local source wheel is qualified with the source-built Core 1.5.0 wheel.
Merge and publication remain blocked until Core 1.5.0 is published and this
exact Python candidate passes installed-wheel and release qualification against
the actual published Core artifacts. Source-candidate integration is additional
evidence; it does not substitute for that post-publication gate.

Scheduled Python jobs only qualify candidates. Manual `release.yml` runs default
to `dry_run: true`; explicitly selecting false is the publication boundary.
Candidate bases must be newer than every stable Git tag and the latest stable
PyPI release. Development qualification refuses a ref missing `main` history.
The workflow atomically pushes the tested version commit and immutable tag
before uploading to PyPI, then fast-forwards `dev` after a stable publication.
The user must authorize deployment before any publishing workflow is dispatched.

If registry upload fails after the atomic ref push, keep the tag. Inspect PyPI
for partial artifacts, compare hashes to the retained workflow artifact and tag,
and resume only the missing upload from those exact validated artifacts. Do not
move the tag, reuse the version for different bytes, or rerun version generation
with an existing release tag. A changed branch must be qualified again.

Core's individual registries have separate availability; never infer that a
Python version is present on npm or crates.io. Native wheel coverage and source
build requirements are documented in Core's platform policy.

## Python finding disposition

All 35 Python findings have a concrete resolution below. Core-owned fixes are
separately tracked in Core's `docs/reviews/2026-11-core-findings.md`; their combined
release still requires Core publication and the published-artifact qualification
above.

| Finding | Resolution and proof                                                                                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PY-H1   | Replace lone surrogates only for native transport, preserving source coordinates. Engine and hook/LiteLLM block regressions cover mixed payloads.                                                                  |
| PY-H2   | Interval queries replace pairwise overlap checks; redaction and legacy assembly are linear after sorting. Dense scan/redaction benchmarks and overlap tests cover the change.                                      |
| PY-H3   | TextService scans complete documents through the shared engine. Boundary-crossing email/SSN tests pass.                                                                                                            |
| PY-H4   | spaCy/GLiNER return actual character spans. Stub and real-spaCy tests distinguish Ann from Annual and repeated names.                                                                                              |
| PY-H5   | Every engine and legacy/CLI path uses the same structured layer before optional NER. Discover/IPv6/credential tests cover the paths.                                                                               |
| PY-M1   | Coroutine decorators await results; non-string results raise a documented TypeError rather than silently escaping inspection.                                                                                      |
| PY-M2   | Redact, replace and hash pipeline operations imply scanning. All three are tested without an explicit SCAN operation.                                                                                              |
| PY-M3   | Fallback email consumes each lexical run once; German separator expressions avoid ambiguous repetition. Adversarial 80K-character measurements and positive matches pass.                                          |
| PY-M4   | Native backend selection also supplies the structured stage of smart/spaCy/GLiNER. CLI commands work with DATAFOG_BACKEND=rust.                                                                                    |
| PY-M5   | Request-scoped tokens, nested tool/function arguments, prompt/input fields and buffered streaming protect all tested request/response shapes. Live proxy deployment is not claimed.                                |
| PY-M6   | Bare strings, invalid labels and labels unavailable to the selected backend/engine raise explicit errors. Supported aliases remain accepted.                                                                       |
| PY-M7   | APIs and CLI honor hash_type, preserve existing plain-hash formats and support full-length keyed HMAC. Plain-hash guessing limitations are documented; algorithm/key and compatibility tests pass.                 |
| PY-M8   | Hook per-string/total budget exhaustion emits review/deny or an incomplete-scan notice. Tests put PII past the cap.                                                                                                |
| PY-M9   | Allowlist expressions run with match timeouts; timed-out expressions retain findings. Adversarial patterns and safe quantified groups are tested.                                                                  |
| PY-M10  | Dependency resolution stays within the explicitly reviewed Core minor, replacing the broad less-than-2 range. Exact output locks should still pin patch versions.                                                  |
| PY-M11  | Reconcile stable history, reject stale/PyPI-occupied versions, gate 3.13, sync version metadata and push immutable refs before upload. Scheduled runs are nonpublishing; selector tests and actionlint pass.       |
| PY-M12  | Spark maps ordinary PERSON/ORG/GPE/NORP/DATE labels into its fixed output schema. Stub tests cover real spaCy label spellings and oversized input errors.                                                          |
| PY-M13  | Optional Pydantic fields have defaults, labels use canonical names, enum filters work and overlaps merge before replacement. Model/anonymizer regressions pass.                                                    |
| PY-M14  | Preserve supported GLiNER labels, use exact offsets, exclude relative spaCy DATE mentions, propagate model failures and reject oversized annotator input explicitly.                                               |
| PY-M15  | Embedded model calls use bounded overlapping chunks. Large PERSON/ADDRESS plus structured-PII tests succeed with published and candidate Core. Native model limits remain enforced.                                |
| PY-M16  | Core 1.5 excludes phone-plus-ZIP card candidates. Candidate seam tests assert PHONE/ZIP labels and no false card.                                                                                                  |
| PY-L1   | Console bootstrap prints the CLI-extra install hint on a base install. A clean installed-wheel check confirms no traceback.                                                                                        |
| PY-L2   | Remove README BOM and stale backend statements, repair contract links and make the German example explicitly select its locale/entity. Core 1.5 suppresses the labelled-tax-ID PHONE false positive.               |
| PY-L3   | Retirement notices derive the current supported release version, and the native install hint no longer names an older release.                                                                                     |
| PY-L4   | Supported-entity reporting follows the selected native/Python capability inventory, including opt-in labels. Tests separate supported from default-active labels.                                                  |
| PY-L5   | Document actual token/pseudonym outputs and reject invalid methods in both process APIs.                                                                                                                           |
| PY-L6   | Legacy APIs and TextPIIAnnotator route through the shared engine; service/engine integration covers native-only entities and locale behavior. Explicit Python fallback remains a narrower documented detector set. |
| PY-L7   | Tokens reuse values and avoid existing markers; invalid explicit ranges/text raise errors. Collision, repeated-value and validation tests pass.                                                                    |
| PY-L8   | Remove unused implementation copies, declare an isolated build, include test packages/corpora/scripts in sdists, align formatter pins and extend tox through 3.14. Optional OCR imports skip cleanly when absent.  |
| PY-L9   | CLI configuration hides API keys; import and commands preserve host logging levels. CLI/logger regressions pass.                                                                                                   |
| PY-L10  | Unicode emails are supported in fallback and candidate Core; Core 1.5 trims embedded PERSON trailing punctuation. Candidate seam tests cover both.                                                                 |
| PY-L11  | TextService validates positive chunk lengths and engine names with explicit exceptions, including optimized Python execution.                                                                                      |
| PY-L12  | Remove incompatible Torch upper bound and include spaCy in nlp-advanced. Resolving it with Core GLiNER2 succeeds with Torch 2.12.0.                                                                                |
| PY-L13  | Declare Pydantic 2.1 minimum. A clean Python 3.10 base install with Pydantic 2.1 imports and scans successfully.                                                                                                   |
| PY-L14  | Correct native-default documentation, normalize missing native metadata to ImportError, clarify missing-model hints, validate locales consistently and surface invalid CLI operations as usage errors.             |
