# Core 0.4 capability adapter integration gate

Status: validated against both the final local candidate and published Core
0.4.0 wheel. Hosted CI results are tracked on Python PR #179. DataFog Python
remains unpublished; merging and release require separate authorization.

## Scope

- Keep Python detection as the default and retain legacy result classes,
  transformation strategies, aliases, full-match allowlists, and overlap order.
- Require Core capability contract version 1 for the Rust backend.
- Accept future finding labels without consulting Python's detector inventory.
- Read text applicability and activation settings from `entities` metadata.
  `PERSON` is structured-only; explicit text selection must fail clearly.
- Derive configuration activations, including UUID opt-in, from metadata.
- Validate explicit locales against the advertised identifiers using trimming
  and ASCII case-insensitive comparison. Preserve the requested locale when
  forwarding to Core. German aliases activate German detection; en-US and fr
  are supported base-only locales. Do not use Python regex locale validation.
- Support Python's plural locales through singular Core scans, then deduplicate
  identical entity labels and source ranges before legacy overlap handling.
- Ignore unrelated additive capability fields. Fail explicitly for incompatible
  contracts or unusable metadata rather than silently falling back to Python.

## Release validation checklist

1. Obtain the finalized candidate wheel and platform support matrix from Core.
2. Validate capability inventory and activation metadata against the candidate.
3. Exercise every new entity through scan, selection, allowlists, and redaction;
   verify Unicode code-point slicing and multiple-locale deduplication.
4. Record reviewed 0.3-to-0.4 differences without changing the frozen 4.8.1
   observations: German coverage, stricter locales, and default JWT, PRIVATE_KEY,
   contextual US_ROUTING_NUMBER, and contextual NPI detection. UUID stays opt-in.
5. Run the base suite without native dependencies and native candidate tests,
   installed-wheel checks, and public-call performance comparisons.
6. Only after candidate validation, change the Rust extra to
   `datafog-core>=0.4.0,<0.5`, update the native parity fixture and CI, and update
   migration documentation to distinguish the new contract from the 0.3.1 bridge.
7. Verify the published Core wheel before publishing Python. No release is
   authorized by this integration work.

## Candidate evidence

The final Core wheel was force-reinstalled and tested on macOS ARM64, CPython
3.12. It reports Core 0.4.0 and capability contract 1.

- Source revision supplied by Core: `60c4636`.
- Artifact: `datafog_core-0.4.0-cp310-abi3-macosx_11_0_arm64.whl`.
- Verified SHA256:
  `351ab81ae575b31a6739a43e29135884ccc0d7152f01df568cd1f7608d690b1c`.
- Focused candidate/adapter/legacy contract suites: **352 passed**.
- Base/CLI regression without native dependency: **833 passed, 19 skipped,
  295 deselected, 19 existing xfails**.
- Frozen corpus: **77 exact matches, two detector differences, one validation
  difference, 31 cases outside backend scope**. All formerly unsupported German
  cases now match. The invalid-card and embedded-SSN differences persist. The
  unknown-locale exception remains `ValueError` with a new capability-based
  diagnostic. Original `4.8.1.json` and historical `rust-0.3.1.json` are unchanged.
- Clean Python wheel installed with the exact Core candidate: isolated smoke test
  and `pip check` passed.
- Sphinx documentation build passed with existing static/autodoc warnings.
- Public scan/redact and cold-start measurements are recorded in
  `../benchmarks/results-core-0.4.json`; compare only like-for-like local runs.
  Median warm Rust scan: 3.23 µs short, 9.40 µs mixed, 7.25 ms for 1 MB sparse.
  Python equivalents: 20.80 µs, 42.86 µs, 127.26 ms. These are candidate-local
  measurements, not universal speed guarantees or a claim of unchanged Core
  0.3.1 detector cost. Validated capabilities are cached per native reader
  identity; reloading/replacing that reader gets a new snapshot.

### Reviewed NPI overlap limitation

Core returns both `PHONE` and `NPI` for `NPI 1234567893`. The legacy adapter
preserves overlap-before-selection and its existing priority: `PHONE` wins.
Consequently, explicit `entity_types=["NPI"]` can return no entities; default
legacy redaction still protects the number as a phone. Native `datafog.v5.scan`
retains both findings, and native transformation can explicitly select `NPI`.

This is an intentional compatibility limitation, not complete NPI parity.
A regression test asserts this exact behavior. No new hardcoded entity
priorities or selection-order changes were introduced. Any future change needs
an explicit overlap-policy decision rather than silently changing legacy output.

The supported dependency range is `>=0.4.0,<0.5`. Local candidate validation
was followed by published-artifact validation below. Do not treat local macOS
validation as a cross-platform CI result.

## Published artifact validation

A fresh virtual environment installed the built Python wheel with `[test,cli,rust]`
using `--no-cache-dir --index-url https://pypi.org/simple`, without a local Core
wheel or editable Core checkout. The normal resolver selected published Core
0.4.0 after an initial index propagation delay.

- Publication source: `133bceff0d2a53a7f6d1a75693330c1797285654`, tag
  `python-v0.4.0` (Core publish run `36496967055`).
- Registry artifact: `datafog_core-0.4.0-cp310-abi3-macosx_11_0_arm64.whl`.
- Download origin: `files.pythonhosted.org`, recorded by pip's installation report.
- Published SHA256, matching PyPI release metadata:
  `b4217c2a9834cb774d89a13b9543166dd7f38512a233b1c80984ea9c07c5162c`.
- Installed-wheel smoke with `python -I`: passed.
- `pip check`: passed.
- Published Core / adapter / unchanged legacy contract tests: **352 passed**.
- Frozen native comparison: **77 matches, two detector differences, one
  validation difference, 31 outside-scope cases**, unchanged from the candidate.

The earlier hosted Rust jobs failed only because PyPI did not yet offer Core
0.4.0. Those failed jobs were retried after publication; the current PR head's
CI checks remain the authority for cross-platform readiness. Nothing in this
validation publishes or merges DataFog Python.
