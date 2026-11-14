# Migrating to DataFog 4.10.0

4.10.0 turns on the native engine. Nothing is removed; most callers change
nothing at all. This page covers what a version number cannot: what you will
notice, and what to do if you do not want it.

```bash
python -m pip install --upgrade "datafog==4.10.0"
```

`datafog-core` is now a normal dependency, so this pulls a platform wheel. On
Linux (glibc or musl, x86_64/aarch64/s390x/ppc64le), macOS and Windows
(amd64/arm64) that is a wheel. Elsewhere it builds from source and needs Rust
1.88+. If Core is missing at runtime, detection falls back to the Python engine
and warns once instead of failing.

## What changes

`backend` defaults to `auto`. `auto` selects the native engine when Core
imports, and the Python engine otherwise. `backend="python"` and
`backend="rust"` work exactly as before. `DATAFOG_BACKEND` sets the default
without touching code:

```bash
DATAFOG_BACKEND=python   # always the pure-Python engine, no warning
DATAFOG_BACKEND=auto     # the default
```

`auto` never picks the native engine for `engine="spacy"`, `"gliner"` or
`"smart"`, because the native path serves `engine="regex"` plus embedded-model
findings. Those engines still run on the Python ML stack and still need their
extras.

## Detection differences

The native engine finds things the Python regex engine never did: `API_KEY`,
`BEARER_TOKEN`, `JWT`, `PRIVATE_KEY`, `CREDENTIAL_URI`, `ACCOUNT_NUMBER`,
`US_ROUTING_NUMBER`, `NPI`, `UUID`, and the German identifier set behind the
`de` locale. Credential detectors ship enabled by default; German and `UUID`
stay opt-in.

These differences go the other way and are recorded, not hidden, in
[tests/contracts/rust-1.2.0.json](../tests/contracts/rust-1.2.0.json):

| Input | Python | Native | Why |
| --- | --- | --- | --- |
| `4111 1111 1111 1112` | `CREDIT_CARD` | none | Core validates the Luhn checksum |
| `x123-45-6789y` | `SSN` | none | Core requires non-alphanumeric boundaries |
| `Invoice 1234567890` | `PHONE` | none | Core requires an area code starting 2-9, which is what keeps Unix timestamps out of `PHONE` |
| `unsupported` locale | locale ignored | `ValueError` | Core validates locales against its inventory |

`PERSON` and `ADDRESS` used to need spaCy or GLiNER through `[nlp]` and
`[nlp-advanced]`. They now come from an embedded model on the native path, with
no download and no interpreter. `PERSON` for a text scan on `backend="python"`
is still Python-engine territory: the pure-Python regex engine has no name
detection, so select `PERSON` without forcing `backend="python"`.

## If the output must not move

Pin the backend, not just the version:

```python
import datafog

datafog.scan(text, backend="python")        # exact 4.9.0 output
```

Or pin the whole package: `pip install "datafog==4.9.0"`.

Detection output is part of the contract. Per
[VERSIONING.md](../VERSIONING.md), a change to the finding set is a MINOR, never
a PATCH, so a patch release will not move your golden files.

## Reproducibility

Core versions independently. If output must be byte-identical across machines,
lock it:

```bash
pip install "datafog==4.10.0" "datafog-core==1.2.0"
```

`datafog.native.version()` reports the installed engine version and
`datafog.native.contract_version()` the contract it speaks, for bug reports.
Core follows its own [versioning policy](https://github.com/DataFog/datafog-core/blob/main/VERSIONING.md);
a contract bump is a Core MAJOR and raises the floor here.

## What is not changing yet

`detect()`, `process()`, OCR and Spark all still work and still warn. They are
removed in 5.0, not here. The last supported version is 4.10.0 — see the
[retirement schedule](retirement.rst).
