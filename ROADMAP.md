# DataFog Roadmap

_Last updated: July 2026 — following the [v4.5.0 stable release](https://github.com/DataFog/datafog-python/releases/tag/v4.5.0)._

DataFog's direction for v5: **the fastest, easiest offline PII firewall for AI apps, logs, and datasets** — no network calls, no model downloads on import, one obvious API.

Independent benchmarking ranks DataFog fastest among Python PII libraries by orders of magnitude. The v5 cycle invests that speed advantage into precision, EU coverage, and a leaner package.

## v5.0.0 themes

### 1. Precision: validators, confidence scores, strictness presets

Speed means nothing if you can't trust the findings. v5 adds a zero-dependency validation pass on every hit (Luhn for credit cards, IBAN mod-97, SSN structure rules, IP plausibility), confidence scores on findings, and strictness presets (`strict` / `balanced` / `lenient`) so you pick the precision/recall tradeoff instead of hand-filtering. We'll publish precision/recall benchmarks alongside the speed benchmarks.

### 2. EU language & entity coverage

v4.5.0 introduced German locale support. v5 generalizes it into a locale pack system — new languages become data plus tests, not code changes — starting with locale-independent EU entities (IBAN, VAT IDs, national ID formats) and expanding across FR/ES/IT/NL/PL through the v5.x line.

### 3. A leaner package

The core install stays pydantic-only and tiny. The heavyweight paths are being cut or spun out: the Donut/transformers OCR path goes away (pytesseract remains), the PySpark wrapper becomes a documented recipe, and legacy duplicate modules are deleted. CI enforces wheel-size and import-time budgets.

### 4. Built for pipelines, not just scripts

The core `scan`/`redact` functions are pure, stateless, and thread-safe, with batch/iterator APIs for high-throughput use. Instead of shipping transport connectors, we're publishing recipes for embedding DataFog in Kafka consumers, Vector/Fluent Bit transforms, and OpenTelemetry collector processors.

### 5. Vault-friendly anonymization

Deterministic tokenization with exportable mappings and format-preserving pseudonymization, so DataFog slots into vault-and-token architectures rather than competing with them.

## API direction

`scan()`, `redact()`, and `protect()` — shipped as previews in v4.5.0 — become the primary documented API in v5.0.0. The legacy `detect()`/`process()` functions keep working as compatibility shims throughout the v5.x line.

## Feedback

Roadmap priorities are shaped by user feedback — open a [GitHub issue](https://github.com/DataFog/datafog-python/issues) or join the [Discord](https://discord.gg/bzDth394R4).
