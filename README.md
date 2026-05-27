# DataFog Python

DataFog is a Python library for detecting and redacting personally identifiable information (PII).

It provides:

- Fast structured PII detection via regex
- Optional NER support via spaCy and GLiNER
- A simple agent-oriented API for LLM applications
- Backward-compatible `DataFog` and `TextService` classes

## 4.5 Focus

DataFog 4.5 is focused on lightweight text PII screening: a small core install,
fast regex-based scan/redact helpers, explicit optional extras, and a clearer
path toward future middleware use cases. Dedicated Sentry, OpenTelemetry,
logging-framework, and cloud DLP adapters are future-facing work and are not
part of the 4.5 release.

## Installation

```bash
# Core install (regex engine)
pip install datafog

# Add spaCy support
pip install datafog[nlp]

# Add GLiNER + spaCy support
pip install datafog[nlp-advanced]

# Add local OCR support
pip install datafog[ocr]

# Add Spark/distributed support
pip install datafog[distributed]

# Everything
pip install datafog[all]
```

Python 3.13 support is certified for the core SDK, CLI, `nlp`,
`nlp-advanced`, and `ocr` install profiles. Donut OCR still requires a model
that is available locally before runtime use. `distributed` and `all` are not
newly certified on Python 3.13 in the 4.5 line.

## Quick Start

```python
import datafog

text = "Contact john@example.com or call (555) 123-4567"
clean = datafog.sanitize(text, engine="regex")
print(clean)
# Contact [EMAIL_1] or call [PHONE_1]
```

## For LLM Applications

```python
import datafog

# 1) Scan prompt text before sending to an LLM
prompt = "My SSN is 123-45-6789"
scan_result = datafog.scan_prompt(prompt, engine="regex")
if scan_result.entities:
    print(f"Detected {len(scan_result.entities)} PII entities")

# 2) Redact model output before returning it
output = "Email me at jane.doe@example.com"
safe_result = datafog.filter_output(output, engine="regex")
print(safe_result.redacted_text)
# Email me at [EMAIL_1]

# 3) One-liner redaction
print(datafog.sanitize("Card: 4111-1111-1111-1111", engine="regex"))
# Card: [CREDIT_CARD_1]
```

## German Structured PII

German structured PII is country-specific and opt-in. Use explicit locale
selection or entity-type filtering when you want German VAT IDs, German IBANs,
tax IDs, postal codes, passports, or residence permits.

```python
import datafog

text = "Steuer-ID 12345678901 liegt vor."

print(datafog.scan(text, engine="regex").entities)
# []

print(datafog.scan(text, engine="regex", locales=["de"]).entities)
# [Entity(type='DE_TAX_ID', text='12345678901', ...)]
```

### Guardrails

```python
import datafog

# Reusable guardrail object
guard = datafog.create_guardrail(engine="regex", on_detect="redact")

@guard
def call_llm() -> str:
    return "Send to admin@example.com"

print(call_llm())
# Send to [EMAIL_1]
```

## Engines

Use the engine that matches your accuracy and dependency constraints:

- `regex`:
  - Fastest and always available.
  - Best for default structured entities: `EMAIL`, `PHONE`, `SSN`, `CREDIT_CARD`, `IP_ADDRESS`, `DATE`, `ZIP_CODE`.
  - Use `locales=["de"]` for German structured IDs such as `DE_VAT_ID`, `DE_IBAN`, `DE_TAX_ID`, `DE_POSTAL_CODE`, and passport or residence permit numbers.
- `spacy`:
  - Requires `pip install datafog[nlp]`.
  - Useful for unstructured entities like person and organization names.
- `gliner`:
  - Requires `pip install datafog[nlp-advanced]`.
  - Stronger NER coverage than regex for unstructured text.
- `smart`:
  - Cascades regex with optional NER engines.
  - If optional deps are missing, it degrades gracefully and warns.

## Optional OCR And Spark Surfaces

DataFog 4.5 keeps the main package story centered on lightweight text PII
screening. OCR and Spark remain supported optional surfaces for users who
already rely on them, but they are not required for the core import, default
scan/redact helpers, or guardrail helpers.

- OCR:
  - Install `datafog[ocr]` for local image OCR helpers.
  - URL-based image downloading also needs `datafog[web,ocr]`.
  - Tesseract usage requires the system `tesseract` binary.
  - Python 3.13 is validated for the OCR install profile, Pillow,
    pytesseract, and system Tesseract smoke checks.
  - Donut OCR requires `datafog[nlp-advanced,ocr]` and a model already available
    locally.
- Spark:
  - Install `datafog[distributed]` for `SparkService`.
  - Spark PII UDF helpers also require `datafog[nlp]` and an installed spaCy
    model.
  - A Java runtime is required by PySpark.

OCR and Spark are not deprecated. Their broader API and packaging overhaul is
deferred; the 4.5 goal is to keep them explicit, documented, and isolated from
the lightweight core path.

## Backward-Compatible APIs

The existing public API remains available.

### `DataFog` class

```python
from datafog import DataFog

result = DataFog().scan_text("Email john@example.com")
print(result["EMAIL"])
```

### `TextService` class

```python
from datafog.services import TextService

service = TextService(engine="regex")
result = service.annotate_text_sync("Call (555) 123-4567")
print(result["PHONE"])
```

## CLI

```bash
# Scan text
datafog scan-text "john@example.com"

# Redact text
datafog redact-text "john@example.com"

# Replace text with pseudonyms
datafog replace-text "john@example.com"

# Hash detected entities
datafog hash-text "john@example.com"

# Enable German regex identifiers
datafog redact-text "Steuer-ID 12345678901" --locale de
```

## Telemetry

DataFog telemetry is disabled by default.

To opt in:

```bash
export DATAFOG_TELEMETRY=1
```

To force telemetry off:

```bash
export DATAFOG_NO_TELEMETRY=1
# or
export DO_NOT_TRACK=1
```

Telemetry does not include input text or detected PII values.

## Development

```bash
git clone https://github.com/datafog/datafog-python
cd datafog-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all,dev]"
pip install -r requirements-dev.txt
pytest tests/
```
