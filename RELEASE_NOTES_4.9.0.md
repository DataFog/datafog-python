# DataFog Python 4.9.0

4.9.0 bridges the existing Python API and DataFog Core. **Python detection remains
the default.** Existing imports, result classes, and legacy redaction strategies
continue to work. Rust detection and the native API preview are experimental,
explicit opt-ins.

## Upgrade

```bash
# Base package: no native dependency is automatically installed.
python -m pip install --upgrade "datafog==4.9.0"

# Optional Rust backend and native API preview.
python -m pip install --upgrade "datafog[rust]==4.9.0"
```

The Rust extra requires `datafog-core>=0.4.0,<0.5` and capability contract `1`.
Installing it does not select Rust automatically. The `all` extra does not
include Rust; request `datafog[all,rust]==4.9.0` if both are needed. Lock your Core
version when detection output must be reproducible across installations.

```python
import datafog

result = datafog.redact("Contact jane@example.com", engine="regex", backend="rust")
assert result.redacted_text == "Contact [EMAIL_1]"
```

Rust is supported only with `engine="regex"`. Missing dependencies, unsupported
configurations, and native failures raise errors without silently falling back.
The CLI, `DataFog`, `TextService`, ML engines, and existing integrations retain
their current detection paths.

## What changes

- `datafog.compat.v4` exposes existing scan/redact APIs and result classes with
  the same class identity as the established Python API.
- `datafog.v5` exposes native Core types and operations. Scanning returns
  `list[Finding]`; native transformations return `TransformResult`, use Core's
  strategies, and do not promise legacy numbered tokens or plaintext mappings.
- Rust detector labels, supported locales, and opt-in settings come from Core's
  capability metadata. Core 0.4.0 supports the seven German detectors through
  German locales or explicit entity selection. UUID remains opt-in. Core's
  structured-only `PERSON` is rejected for explicit Rust text selection.
- Core 0.4.0 adds JWT, private-key, contextual US routing-number, and contextual
  NPI detection. Python allowlists and legacy transformations remain in the
  compatibility adapter.

## Known differences

Rust is not advertised as universally equivalent to the Python detector. On the
frozen 111-case baseline there are 77 exact matches, two reviewed detector
differences, one validation-message difference, and 31 cases outside backend
scope. Core rejects invalid-checksum cards and alphanumeric-embedded SSNs in the
reviewed differing cases. Unsupported locale validation uses Core capabilities.

**Explicit NPI selection has a compatibility limitation:** when Core reports both
`PHONE` and `NPI` for the same span, legacy overlap handling keeps `PHONE` before
entity filtering. Consequently `entity_types=["NPI"]` can return no entities.
Default legacy redaction still protects that span as a phone. Native
`datafog.v5.scan()` retains NPI, and native transformation can select it. Choose
the native API when retaining NPI identity is required.

The adapter resolves overlaps before entity filtering. A later compatible Core
release can introduce a finding that wins an overlap and suppresses a previously
selected label. The dependency range promises API compatibility, not identical
detection or selection results. For reproducible behavior, pin both packages:

```bash
python -m pip install "datafog[rust]==4.9.0" "datafog-core==0.4.0"
```

Use native findings and native transformation entity selection when preserving
specific overlapping labels is required.

## Deprecations for 5.0

`detect()` and `process()` still work in 4.9 but now warn of removal in 5.0. This
revises the earlier promise to retain them throughout 5.x. Migrate to scan/redact
and review transformation differences, particularly older placeholder and hash
formats.

OCR, Donut, Tesseract, image services, Spark, and distributed helpers remain
functional in 4.9 with visible use-time warnings. Their removal is planned for
5.0. Users needing them can remain on the final 4.x release; this does not promise
indefinite maintenance or introduce successor packages. spaCy and GLiNER are not
removed by this release.

See the [migration guide](https://github.com/DataFog/datafog-python/blob/v4.9.0/docs/migration-4.9.md) for API examples, compatibility
boundaries, parity evidence, and reproducible verification commands.
