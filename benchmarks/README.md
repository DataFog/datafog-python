# DataFog benchmarks

Every performance number DataFog publishes should be reproducible by a
skeptic with one command. This directory is that command:

```bash
pip install -e . -r benchmarks/requirements.txt
python -m spacy download en_core_web_sm   # comparison suites only
python benchmarks/run.py
```

Suites that are missing optional dependencies are skipped with an install
hint — `python benchmarks/run.py --suite core,hook` runs with nothing but
datafog itself installed. `--json results.json` writes machine-readable
output; `--quick` is a fast smoke run (fewer repeats, large payloads
skipped).

## Methodology

- **In-process timings** use stdlib `timeit`: `Timer.autorange()` picks an
  inner loop count so each timed repeat runs ≥0.2s, then 5 repeats (3 in
  comparison suites) are reported as median ± stdev. No mocking — every
  call goes through the same public code path a user hits.
- **The hook suite measures wall-clock subprocess time**: a fresh
  `datafog-hook` process per iteration, JSON payload on stdin, exactly as
  Claude Code invokes it. 3 warmup runs, 30 timed runs, median and p90
  reported. Python interpreter startup is *included* — that is the honest
  cost of a per-tool-call hook.
- **Pinned payloads** live in [payloads/](payloads/) and are checked in,
  not generated at runtime. [payloads/manifest.json](payloads/manifest.json)
  records the entity counts the regex engine must find in each payload; the
  runner verifies those counts *before* timing anything, so the suite fails
  loudly rather than silently benchmarking an engine that stopped
  detecting. All PII values are industry-standard synthetic test data
  (reserved `.invalid`/`example.com` domains, fictional 555-01XX phone
  numbers, public Luhn-valid test cards, SSA example SSNs).

| Payload | Size | Content |
| --- | --- | --- |
| `core_1kb_dense.txt` | 1.2 KB | support ticket, 8 entities (PII-dense) |
| `core_10kb_mixed.txt` | 10 KB | business document, 12 entities in prose |
| `core_100kb_sparse.txt` | 100 KB | machine logs, 18 entities among UUIDs/timestamps (false-positive pressure) |
| `chat_request_clean.json` | — | 2-message LiteLLM chat body, no PII |
| `chat_request_pii.json` | — | 2-message LiteLLM chat body, email + card + phone |
| `hook_pretooluse.json` | — | Claude Code `PreToolUse` payload, `curl` command carrying PII |

All suites use the production default entity set
(`EMAIL, PHONE, CREDIT_CARD, SSN`).

## Reference results

Apple M5 Pro, macOS, CPython 3.13, datafog 4.7.0, litellm 1.91.0,
presidio-analyzer 2.2.363, spaCy 3.8 (`en_core_web_sm`). Medians of the
full (non-quick) run; expect different absolute numbers on different
hardware, but the ratios and orders of magnitude should hold.

### core — `datafog.scan` / `datafog.redact`, regex engine

| Operation | Median | Throughput |
| --- | --- | --- |
| scan 1.2 KB dense | 231 µs | 5.3 MB/s |
| redact 1.2 KB dense | 240 µs | 5.1 MB/s |
| scan 10 KB mixed | 1.20 ms | 8.6 MB/s |
| redact 10 KB mixed | 1.19 ms | 8.6 MB/s |
| scan 100 KB sparse | 11.9 ms | 8.4 MB/s |
| redact 100 KB sparse | 12.1 ms | 8.3 MB/s |

### guardrail — `DataFogGuardrail` (LiteLLM), in-process

| Operation | Median |
| --- | --- |
| single message redact | 43 µs |
| `pre_call`, clean 2-message request | 118 µs |
| `pre_call`, PII 2-message request (redact) | 222 µs |
| event-loop dispatch (harness overhead, included above) | 27 µs |

The PII-request figure includes litellm's own guardrail-intervention
logging (~85 µs), not just detection. In a live proxy the event loop is
already running, so the ~27 µs dispatch overhead in the two per-request
rows is an artifact of benchmarking with `run_until_complete`.

### hook — `datafog-hook` (Claude Code)

| Operation | Median |
| --- | --- |
| end-to-end subprocess, incl. Python startup | 69–89 ms across runs (p90 ~77–96 ms) |
| the scan itself (in-process) | 75 µs |

The end-to-end cost is ~99.9% Python interpreter + import startup; the
scan is microseconds. Cold (first-ever) invocations can spike to several
hundred ms while the OS warms caches — the warmup runs exclude that, the
p90 shows steady-state spread.

### Comparisons — same payloads, same four entity types

Both comparison targets are pinned to `en_core_web_sm`, the *smallest*
English spaCy model — deliberately favorable to them (smaller model =
faster inference), so these ratios are lower bounds. Model/engine setup
time (~0.1–1 s) is excluded from per-scan figures. Presidio runs in-process
via `AnalyzerEngine` with a documented `NlpEngineProvider` config — no
sidecar, no network hop, which again flatters Presidio relative to its
usual proxy deployment.

| Payload | datafog regex | Presidio | spaCy NER | datafog vs Presidio | datafog vs spaCy |
| --- | --- | --- | --- | --- | --- |
| 1.2 KB dense | 222–251 µs | 22.8 ms | 28.6 ms | 103x | 114x |
| 10 KB mixed | 1.2 ms | 174 ms | 171 ms | 148x | 140x |
| 100 KB sparse | 11.9–12.2 ms | 2.02 s | 1.60 s | 170x | 131x |

Speed is not the only axis: the runner records what each engine actually
detected on each payload (see the `detected` metadata in the output).
Recall differs in both directions — e.g. Presidio's email recognizer does
not match addresses on the reserved `.invalid` domain, and context-based
scoring drops some entities the regex engine finds; conversely NER models
detect names and locations the regex engine does not target at all. The
comparison is a fair *speed* comparison on identical inputs and entity
types, not an accuracy study.

## How these map to published claims

- **"~31µs per request" (LiteLLM guardrail, project README /
  datafog.ai)** — not reproduced *as worded*. ~31–43 µs is the cost of
  scanning/redacting **one short message**; a full 2-message request
  through `async_pre_call_hook` is ~120 µs clean / ~220 µs with redaction
  and litellm logging. Still 100–1000x below a sidecar's network hop, but
  the claim should be reworded to per-message, e.g. *"~40µs per message —
  a request clears the guardrail in well under a millisecond"*. Reproduce:
  `python benchmarks/run.py --suite guardrail`.
- **"~70ms per invocation including process startup" (Claude Code
  hook)** — reproduced: 69–89 ms median across runs on this machine
  (~70 ms idle, higher under load), dominated by interpreter startup.
  *"~70–90ms"* (or "under 100ms") is the defensible phrasing. Reproduce: `python benchmarks/run.py --suite hook`.
- **"190x performance advantage" (PyPI tagline)** — not reproduced at
  190x by this suite. Measured: 103–170x vs Presidio and 114–140x vs spaCy
  NER, varying by payload. The historical 190x came from a different
  (13.3 KB, entity-dense) document and engine configuration. Honest
  phrasings this suite supports: *"100x+ faster than NER-based PII
  detection"* or *"up to 170x faster than Presidio on identical
  payloads"*. Reproduce: `python benchmarks/run.py --suite spacy,presidio`.

## Fairness notes / known limitations

- Single-threaded, single-machine, synthetic payloads. Real chat traffic
  and real documents will differ; the payloads are designed to bracket the
  realistic range (dense, mixed, sparse).
- `timeit` medians hide GC pauses and tail latency by design; the hook
  suite's p90 is the only tail-latency figure here.
- The comparison suites measure the engines *as configured here*
  (documented model, in-process, setup excluded). Different Presidio
  recognizer registries or larger spaCy models change both speed and
  recall — in Presidio's favor on recall, against it on speed.
