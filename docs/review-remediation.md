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
The engine also accepts algorithms provided by hashlib. Digests use full hex
lengths. Plain deterministic hashes are pseudonymization: SSNs, phones and
other guessable inputs can be enumerated. Use `hash_key` (at least 32 random
bytes) for keyed HMAC and keep the key outside logs and source control:

```python
import secrets
import datafog
key = secrets.token_bytes(32)  # store securely to reproduce pseudonyms
result = datafog.redact("mail jane@example.com", strategy="hash", hash_key=key)
```

## Release sequence and qualification

The Python candidate is 4.12.0. Its standalone CI uses the published Core 1.4
minor series, pinned with `~=1.4.0`. Core 2.0.0 is prepared separately because
safe mask-reveal and automatic-overlap transformation semantics are incompatible
changes under Core's version policy. Both use capability contract 1. Before
shipping the combined fixes, publish the qualified Core candidate, then raise
both Python dependency declarations to `~=2.0.0`, update the reviewed native
contract/corpus, and run Python's installed-wheel and release qualification
against the published artifacts. Source-candidate integration is additional
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
