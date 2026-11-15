# DataFog 4.12.0

DataFog 4.12.0 carries structured PII detection through every engine, legacy
API and CLI anonymization path. Smart, spaCy and GLiNER modes retain the same
native card, IP and credential findings as the regex mode, then add NER spans.
TextService scans complete documents, and spaCy/GLiNER character offsets prevent
an earlier substring or repeated name from receiving the wrong redaction.

This candidate requires `datafog-core~=1.5.0` in the base package and the `rust`
extra. Core 1.5 supplies complete IPv4-mapped IPv6 redaction, corrected email
field boundaries and Unicode mailboxes, and phone-plus-ZIP classification that
does not suppress the phone behind a false card finding. Native differences
are recorded in `tests/contracts/rust-1.5.0.json`. Capability contract 1 remains
unchanged; Python and Core have independent version numbers.

Lone surrogate characters no longer disable native scans. Dense overlap
suppression, Python fallback patterns and allowlist matching have bounded work;
typoed entity labels, invalid ranges and invalid locales raise explicit errors.
Anonymizing pipeline operations imply scanning. Async guardrail decorators
await their result, and non-string results raise TypeError.

LiteLLM scans nested tool/function arguments and prompt/input requests with a
shared token assignment for the request. Repeated values reuse tokens, and
existing markers do not collide. Streaming buffers the complete upstream
response before emitting its first redacted chunk, including text and tool
arguments split across deltas. This adds the full upstream completion latency
to first output. Streams exceeding eight million text characters or 100,000
chunks are rejected. Engine errors retain the configured `open` or `closed`
failure policy. Image and binary parts remain opaque and receive no OCR.

The Claude Code hook asks for review, or denies according to configuration,
when input exceeds its scan budget; it no longer silently permits an unscanned
tail. Unexpected hook failures retain the documented fail-open policy.

Hash APIs honor the selected algorithm while preserving existing plain-hash
formats. Engine APIs, the DataFog class and CLI retain SHA-256 with 12 hex
characters by default. Deprecated top-level `datafog.process(method="hash")`
retains MD5 with eight hex characters. The legacy Anonymizer model retains its
existing full plain digest. Explicit `hash_key` adds full-length HMAC with at
least 32 key bytes; omitting the algorithm in keyed mode selects SHA-256.
Unkeyed hashes remain guessable deterministic pseudonyms, not protection
against enumerating SSNs, phone numbers or other low-entropy values.

The minimum Pydantic version is 2.1. The `nlp-advanced` extra includes spaCy and
permits Torch 2.x versions compatible with Core's GLiNER2 extra. Base installs
show a CLI-extra installation hint instead of a missing-Typer traceback.
Unused duplicate implementations are removed, source distributions include
runnable tests and corpora, and CLI configuration output hides API keys.

Scheduled release jobs qualify candidates without publishing. Manual jobs
default to dry runs, reject stale or occupied versions, and record immutable
release refs before uploading artifacts.

This is a release candidate prepared for review. Core 1.5 publication and
qualification of this Python candidate against the actual published Core
artifacts remain mandatory before merge and release. Local source-wheel
qualification does not claim either package has been published.
