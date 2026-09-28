# DataFog 4.9: incremental Core migration

## Outcome

Deliver a bridge release that lets users adopt Rust detection and the Core schema
without changing the default Python behavior. Keep the published 4.8.1 contract
as immutable evidence, with narrowly documented 4.9 API additions and revised
deprecation messages. This work does not publish a release or perform the 5.0
cutover.

## Release decisions

- Keep `pip install datafog` and existing top-level imports working in 4.9.
- Add optional `datafog[rust]`, pinned to the published Core version verified by
  this change. Loading the base package must not import the native extension.
- Add keyword-only `backend="python"` to scan/redact entry points. Rust is an
  explicit, experimental alternative for `engine="regex"` only.
- Introduce `datafog.compat.v4` for existing scan/redact APIs and result classes;
  top-level scan/redact delegate there while preserving class identity.
- Introduce `datafog.v5` as a preview of Core's actual public types and functions,
  without translating them into legacy result objects or strategies.
- Revise `detect()` and `process()` warnings: removal is planned for 5.0, replacing
  the earlier promise to retain them throughout 5.x. Explain the change publicly.
- Deprecate OCR and Spark in 4.9; remove them in 5.0. Preserve existing optional
  installations and behavior during 4.9, and warn at meaningful use sites.
- Leave ML engines, smart/auto composition, CLI text commands, application
  integrations, and service APIs on their existing backend in this increment.
- Keep the existing package version until release preparation; this branch
  implements 4.9 behavior but does not publish or stamp a final release.

## Increment 1: opt-in Rust detection

1. Extend `datafog.engine.scan` and `scan_and_redact` with keyword-only backend
   selection, preserving original parameters, validation and Python defaults.
2. Lazily call the installed `datafog_core.scan`; convert findings to existing
   Entity objects using code-point offsets, not byte offsets. Preserve document
   order, original text, and legacy regex provenance/confidence conventions.
3. Keep Python allowlist validation/filtering, aliases and transformation logic.
   Do not reimplement detectors in the adapter or invoke Core transformations.
4. Reject Rust plus non-regex engines, unsupported German locale/entity requests,
   and invalid backend values explicitly. Missing native dependencies must give
   an actionable installation error. Never silently retry with Python or return
   an empty result on native failure.
5. Explicit-entity redaction must not scan or import the native extension.
6. Add focused tests for routing, Unicode, validation, selection, overlaps,
   allowlists, replacement strategies, missing dependencies and propagated errors.

## Increment 2: compatibility namespace and schema preview

1. Make `datafog.compat.v4` the facade for existing scan/redact return shapes and
   result classes; retain legacy engine implementation in place where relocation
   would break internal imports or monkeypatching contracts.
2. Keep top-level functions and types available and forward backend selection.
   Existing agent convenience functions already accept forwarding keyword args.
3. Export the tested Core API through `datafog.v5`, preserving native type
   identity. No Core import on plain `import datafog`; clear optional-dependency
   errors when the preview is used without the extra.
4. Update detect/process warnings and test the explicit revised removal policy.
   Do not expose these functions through the new preview.
5. Test import isolation, facade identity, unchanged legacy results, and real
   Core scanning/transformation through the preview.

## Increment 3: retirement notices for optional legacy surfaces

1. Warn on meaningful OCR/Spark use, including direct supported entry points,
   without importing heavy dependencies merely to issue a warning.
2. Keep those extras and functionality available throughout 4.9. Document removal
   in 5.0 and the option to remain on the final 4.x release. Do not create new
   replacement packages as part of this work.
3. Add tests proving notices are emitted and core text imports stay unaffected.

## Increment 4: integration and evidence

1. Keep the 4.8.1 fixture unchanged. Represent approved signature additions and
   warning-message changes explicitly in the 4.9 contract checker; compare all
   other observed behavior exactly. No blanket skips or recapture from dev.
2. Run applicable cases through the real published Core wheel and produce a
   per-case parity report. Separate matches, deliberate unsupported requests,
   known detector differences and regressions. Experimental Rust detection must
   not be advertised as a drop-in equivalent before gaps are closed.
3. Add CI jobs with and without the Rust extra; smoke-test installed wheels and
   native preview behavior on supported Python/platform combinations.
4. Benchmark the public Python and Rust-backed APIs, including conversion and
   cold startup, with short, mixed and large synthetic inputs. Keep results
   reproducible and make no unsupported speedup claim.
5. Update README, migration documentation and release notes for the actual scope.
6. Run focused suites, broader core regression tests, applicable benchmarks and
   pre-commit checks; open a PR against dev and resolve CI failures.

## Work ownership

- Backend agent: engine backend adapter and focused backend tests.
- API agent: compatibility namespace, preview API, top-level delegation and
  detect/process retirement warnings, with focused tests.
- Retirement agent: OCR/Spark notices and related tests/documentation.
- Coordinator: packaging, contract integration, parity report, CI, benchmarks,
  cross-agent review, final verification and PR.

Agents share one feature branch and have disjoint file ownership. They must not
commit, push, merge, overwrite another agent's files or edit frozen fixtures.
The coordinator reviews and integrates each change before committing.

## Completion criteria

- Default legacy behavior is unchanged except for the documented revised notices.
- Rust use is explicit, installation is optional, failures are visible, and
  coverage limitations are documented and exercised by tests.
- Compatibility and native-preview APIs coexist without duplicated native builds.
- OCR/Spark and detect/process have actionable 5.0 retirement notices.
- Tests, installed-wheel checks, parity evidence and benchmarks are reproducible.
- A reviewed, passing PR is ready for dev; merging is subject to user direction
  and existing repository approval rules.

## Confirmed scope and delivery

The user confirmed retaining deprecated OCR/Spark functionality in 4.9 and
removing it in 5.0. The coordinator is authorized to merge after checks and
required approvals pass; repository protections remain in effect.

German detector expansion is specified separately in
`GERMAN-PII-CORE-REQUIREMENTS.md`. Implementing or publishing those Core changes
is outside this Python bridge increment. Rust calls requiring that unavailable
coverage must continue to fail explicitly until a tested Core release supports it.

## Implementation evidence

All four increments are implemented on `feature/4.9-core-migration`. Backend,
API, and retirement changes were delegated with disjoint ownership; cross-review
also corrected Windows UTF-8 fixture handling and default-filter CLI notice
visibility. The frozen 4.8.1 fixture is unchanged.

- Base/CLI regression run: 782 passed, with expected optional-dependency skips
  and pre-existing corpus xfails.
- Focused native integration run: 347 passed against published Core 0.3.1.
- Python 3.10 and 3.14 base-only runs: 181 passed each; native/CLI-specific tests
  skip when their optional dependencies are absent.
- Clean installed-wheel smoke test: compatibility facade, native detection,
  native preview, Unicode offsets and transformation all passed.
- Native parity: 61 exact matches, two reviewed detector differences, 17 explicit
  unsupported German requests, 31 cases outside this backend's scope.
- Reproducible local timings are in `benchmarks/results-4.9.json`; they include
  public-call overhead and cold startup, not just Rust scanning time.

CI and required PR approval remain the final merge gates. No package publication
or Core-repository implementation is part of this delivery.
