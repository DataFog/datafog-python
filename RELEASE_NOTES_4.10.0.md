# DataFog Python 4.10.0

4.10.0 turns on the native engine. `pip install datafog` installs `datafog-core`
and detection uses it. Nothing is removed in this release and no call changes
shape; `backend="python"` restores the previous behaviour exactly.

Read the [4.10 migration guide](docs/migration-4.10.md) before upgrading a
pipeline whose output is under test.

## Upgrade

```bash
python -m pip install --upgrade "datafog==4.10.0"
```

Wheels cover Linux (glibc and musl, x86_64/aarch64/s390x/ppc64le), macOS and
Windows (amd64/arm64). Elsewhere the source build needs Rust 1.88+. If Core
cannot be imported, detection falls back to the pure-Python engine and warns
once.

## What changes

- `backend` defaults to `auto`: native when `datafog-core` imports, Python
  otherwise. `DATAFOG_BACKEND` sets the default; `backend="python"` forces the
  fallback. Non-regex engines stay on the Python path.
- `PERSON` and `ADDRESS` for prose now come from an embedded model compiled into
  `datafog-core` — no spaCy, no GLiNER, no model download, no interpreter.
- The native engine adds `API_KEY`, `BEARER_TOKEN`, `JWT`, `PRIVATE_KEY`,
  `CREDENTIAL_URI`, `ACCOUNT_NUMBER`, `US_ROUTING_NUMBER`, `NPI`, `UUID` and the
  German identifiers. Credential detectors are on by default; German and `UUID`
  stay opt-in.
- `datafog.native` exposes the native schema, `capabilities()`, the embedded
  detector and version reporting. Experimental until 5.0.
- `datafog-core` is pinned `>=1.2.0,<2`. Detection output is contract-versioned.

## Detection differences

Four reviewed differences from the Python engine are recorded in
[tests/contracts/rust-1.2.0.json](tests/contracts/rust-1.2.0.json) and asserted
by the suite: Core validates card checksums, requires non-alphanumeric SSN
boundaries, requires a North American area code starting 2-9 (which is what
keeps Unix timestamps out of `PHONE`), and rejects unadvertised locales instead
of ignoring them.

`(555) 123-4567` and similar form data now match: Core keeps the area-code check
and accepts exchange codes starting with 1.

## Deprecations unchanged

`detect()`, `process()`, OCR and Spark still work and still warn; all are removed
in 5.0. Their messages now name `4.10.0` as the last supported version and give
the exact pin. See the [retirement schedule](docs/retirement.rst).

## Notes

- `VERSIONING.md` is new and defines what a version number promises here, with a
  deprecation window, a detection-output rule and a support window.
- Hook invocations cost ~105–110ms including process startup, of which ~20ms is
  the native engine load. `DATAFOG_BACKEND=python` trades that back for coverage.
- `datafog[rust]` remains as an explicit spelling of a dependency the base
  install already has.
