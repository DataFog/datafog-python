# Versioning and compatibility policy

DataFog Python follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).
This document defines what that means here, so a version number is a promise
rather than a guess.

DataFog versions independently of `datafog-core`. See
[Independent versioning](#independent-versioning).

## What the numbers mean

- **MAJOR** (`5.0.0`) — a public API is removed or renamed, an import path moves,
  or a default changes such that working caller code stops working.
- **MINOR** (`4.10.0`) — new capability. New entities, new backends, new extras,
  new commands, new options, and **changes to detection output**.
- **PATCH** (`4.10.1`) — fixes that do not change findings for a given input,
  configuration, and locked dependency set.

### Detection output is a minor change, never a patch

The finding set is part of the contract. A patch release must not start finding
more email addresses, or fewer, for input that already worked. If a fix changes
what is found, it ships as a MINOR and the changelog says which entities moved
and in which direction. People write golden files against this output.

### Dependency-default changes are minor

Raising a floor, dropping support for a Python version, or changing which
backend is used by default is a MINOR. It is never a PATCH.

## Deprecation window

A public API is deprecated in a MINOR, warning at the call boundary, and removed
no earlier than the second following MINOR or 90 days, whichever is longer.

A deprecation warning must name:

1. the exact last version that supports the surface, as an installable pin
   (`pip install "datafog==4.10.0"`), and
2. the MAJOR that removes it.

Warnings fire at the public call boundary, before any optional import, so a plain
`import datafog` never pays for a deprecated surface.

At the removal MAJOR, the removed name stays present as a stub raising
`ImportError` with the same pin, rather than disappearing into an
`AttributeError`.

## Experimental surface

Experimental code is marked as such in its documentation and docstrings. It may
break in a MINOR without a deprecation cycle. Anything unmarked is covered by
this policy.

Currently experimental:

- `datafog.v5` (native Core preview)
- `datafog.core` (from 4.10.0)
- GLiNER2 and other model sessions
- Browser/WASM entry points

## Scope

Covered by this policy:

- top-level `datafog` callables listed in `datafog.__all__`
- `datafog.compat.v4` and its result classes
- the `datafog` CLI and the `datafog-hook` entry point
- `DataFogGuardrail` and the Claude Code hook integration
- documented configuration keys and environment variables
- the finding set for a given engine, entity selection, and locale

Not covered:

- private modules and names beginning with `_`
- `main_lean.py`, `main_original.py`, `__init___original.py` and other
  transitional duplicates
- logging text, warning text, and internal error strings
- model accuracy targets for optional ML engines

## Support window

The current MAJOR receives fixes for its latest two MINOR releases. Older MINORs
receive security fixes only. Every published version stays installable on PyPI
permanently; a retired surface has a final supported version documented in
[`docs/retirement.rst`](docs/retirement.rst), and that version is the answer.

## Independent versioning

`datafog` and `datafog-core` are separate distributions on separate tracks.
`datafog-core` carries the engine; `datafog` carries the application surface.
The transport between them is `capabilities()` and its `contract_version`.
Bumping either `contract_version` or `workspace_contract_version` is MAJOR work
for `datafog-core`, and requires a matching floor in `datafog`.

Both are exposed separately so a bug report is attributable:

```python
import datafog, datafog.native
datafog.__version__         # application version
datafog.native.version()    # engine version
```

## Yanking

A broken PATCH may be yanked on PyPI and replaced by the next PATCH. A broken
MINOR or MAJOR is superseded, not yanked, because dependents are often already
pinned to it; the changelog opens with the replacement version.

## Enforcement

- `RELEASE_NOTES_<version>.md` is required for stable releases.
- The changelog classifies every entry as Added / Changed / Deprecated / Removed
  / Fixed and names the version at which each deprecation ends.
- `scripts/check_rust_install.py` and the parity suite run against the installed
  wheel, not the checkout.

## History

Before 4.10.0 this policy was not written down, and the versioning record shows
it: the 5.0 retirement plan was revised mid-stream (commit `5f5bdbb3`), and the
4.9.0 final publish preceded its own `a1` and `a2` tags. 4.10.0 is the first
release prepared under this policy.
