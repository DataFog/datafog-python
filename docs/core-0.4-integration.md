# Core 0.4 capability adapter integration gate

Status: draft implementation against the proposed capability contract. No Core
candidate wheel has been validated yet. The dependency range remains unchanged
until that gate passes; this branch must not merge or publish in this state.

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

## Pending release gates

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
