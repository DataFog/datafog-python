# v5 Model Selection Requirements

This sheet defines requirements for revisiting DataFog's optional model stack before
locking the v5 core API around specific NLP/OCR backends. It is intentionally a
requirements document, not a model recommendation list.

## Decision Goals

- Pick models that improve adoption by making the first successful result easy,
  trustworthy, and local by default.
- Keep the core SDK fast and lightweight; model-backed engines remain optional.
- Make model behavior explicit enough that users can defend it in privacy,
  security, and compliance reviews.
- Preserve a clean path for future backend swaps without breaking the top-level
  v5 API.

## Must-Haves

### Runtime And Packaging

- No model downloads during import, install, or ordinary SDK calls.
- All model downloads must be explicit CLI/API actions or user-provided local
  paths.
- The core install must not require ML, OCR, Torch, TensorFlow, Java, Spark, or
  system OCR binaries.
- Optional extras must map cleanly to real imports:
  - `nlp` for lightweight NLP engines.
  - `nlp-advanced` for heavier ML NER engines.
  - `ocr` for local image/OCR processing.
  - `distributed` for Spark-style processing.
- Missing dependency and missing model errors must explain the exact install or
  download command.
- Python 3.10, 3.11, and 3.12 must be supported for advertised optional model
  profiles. Python 3.13 support should be advertised only after explicit profile
  validation.
- Models must work in offline mode after explicit download/cache preparation.

### Privacy And Trust

- No network access during inference.
- No telemetry, remote callbacks, model hub lookups, or license checks during
  inference.
- No raw PII should be written to logs, cache names, telemetry, exceptions, or
  debug traces by default.
- Model metadata exposed by DataFog should identify model name/version/source
  without storing detected raw PII.
- Reversible workflows must be opt-in and clearly separated from ordinary
  redaction.

### Detection Contract

- Model outputs must include enough structure for the public result contract:
  entity type, text/span, start/end offsets, confidence when available, and
  engine/source.
- Spans must be deterministic for the same model, text, and settings.
- Entity labels must be mappable into DataFog's canonical entity taxonomy without
  surprising users.
- Model-backed engines must compose with regex detection without duplicating or
  overwriting high-confidence structured entities.
- Failure modes must be predictable: unsupported language, missing model, missing
  optional dependency, and low-confidence results should all be distinguishable.

### Quality Gates

- Candidate models must be benchmarked on DataFog's target corpora before
  adoption.
- Benchmarks must include precision/recall by entity type, not only aggregate F1.
- Structured PII such as email, phone, IP address, SSN, credit cards, dates, and
  ZIP/postal codes should remain regex/validator-first unless a model clearly
  improves quality.
- NER-style entities such as person, organization, location, address, and
  domain-specific identifiers need regression tests with realistic app/log data.
- OCR models must be evaluated separately for text extraction quality and PII
  extraction quality after OCR.

### Operational Fit

- CPU inference must be acceptable for the default advertised workflow.
- GPU-only models are not acceptable as default engines.
- Model size, cold-start time, memory use, and cache footprint must be measured.
- The model must have a usable open license for commercial SDK users.
- The model or provider must have credible maintenance signals and versioned
  artifacts.

## Nice-To-Haves

- Strong multilingual support with per-language quality reporting.
- Quantized or small variants that keep local inference practical.
- ONNX or other portable runtime support for future non-Torch deployments.
- Streaming/chunked inference support or predictable behavior across chunk
  boundaries.
- Custom entity hints or user-provided label sets.
- Confidence calibration good enough to expose threshold controls.
- Batch inference APIs for logs, CSV, and JSONL workflows.
- Clear model cards with training data notes, limitations, and intended use.
- Support for local cache directories that can be controlled by environment
  variable or explicit config.
- Graceful operation on Apple Silicon and common Linux CI runners.

## Disqualifiers

- Requires network access for inference.
- Downloads weights implicitly from ordinary SDK calls.
- License is unclear, non-commercial, or incompatible with SDK distribution.
- Requires a hosted API for core value.
- Requires GPU for reasonable first-use behavior.
- Cannot return stable spans or forces only label-level output.
- Emits raw text or entities through logging, telemetry, or callbacks.
- Adds heavyweight dependencies to the core install.
- Breaks Python version support we already advertise.

## Evaluation Matrix

Each candidate backend should be scored before adoption:

| Area | Required Evidence |
| --- | --- |
| Install footprint | Extra name, package deps, wheel size impact, system deps |
| Runtime footprint | Cold start, warm latency, memory, CPU/GPU requirements |
| Offline behavior | Explicit download path, local cache path, no-network test |
| Quality | Precision/recall by entity type on DataFog corpora |
| Span quality | Offset correctness and deduplication behavior |
| Privacy | No raw PII logs/cache/telemetry, safe error messages |
| Licensing | Model license, dependency licenses, commercial use notes |
| Maintenance | Release cadence, Python compatibility, issue activity |
| API fit | Entity taxonomy mapping, confidence support, batch/chunk support |
| Docs fit | Model card, limitations, user-facing setup instructions |

## Candidate Backend Categories To Evaluate

- Regex plus validators for structured PII and secrets.
- Lightweight NLP NER for person, organization, location, and address entities.
- Advanced local NER models for broader entity coverage and multilingual support.
- OCR text extraction engines for local images/PDF-derived images.
- Document understanding models only if they beat OCR plus text PII extraction
  enough to justify their footprint.
- User-provided backend hooks for teams that already have a preferred model.

## Recommended Selection Policy

- Default v5 behavior should remain regex/validator-first.
- Model-backed engines should be opt-in by engine, policy, or extra.
- DataFog should prefer smaller, reliable local models over maximum leaderboard
  scores if they improve install success and first-use latency.
- Model choices should be version-pinned in docs and CI once advertised.
- A model can be experimental in docs/examples before it becomes part of the
  supported contract.

## Open Questions

- Do we want one recommended advanced NER model, or a pluggable registry with a
  default?
- Should OCR stay Tesseract-first, or should v5 introduce a newer local OCR
  default after benchmarking?
- How much multilingual quality is required for v5.0.0 versus a later release?
- Should Python 3.13 optional-profile support be a v4.5 compatibility release,
  a v5 launch requirement, or both?
- What maximum model download size is acceptable for the default recommended
  advanced profile?
