# DataFog Python

DataFog is a Python library for detecting and redacting personally identifiable information (PII).

It provides:

- Fast structured PII detection via regex
- Optional NER support via spaCy and GLiNER
- A simple agent-oriented API for LLM applications
- Backward-compatible `DataFog` and `TextService` classes

## Installation

```bash
# Core install (regex engine)
pip install datafog

# Add spaCy support
pip install datafog[nlp]

# Add GLiNER + spaCy support
pip install datafog[nlp-advanced]

# Everything
pip install datafog[all]
```

Python 3.13 support is certified for the core SDK and CLI. Optional extras such
as `nlp`, `nlp-advanced`, `ocr`, `distributed`, and `all` are available but not
yet certified on Python 3.13.

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

### Streaming Outputs

```python
import datafog

chunks = ["Contact adm", "in@example", ".com"]

for safe_chunk in datafog.filter_stream(chunks, engine="regex"):
    print(safe_chunk)
# Contact [EMAIL_1]
```

The v5.0 streaming filter buffers chunks before emitting output so PII split
across chunk boundaries is still detected. Async streams use
`datafog.filter_async_stream(...)` with the same privacy-first buffering
behavior.

## Engines

Use the engine that matches your accuracy and dependency constraints:

- `regex`:
  - Fastest and always available.
  - Best for structured entities: `EMAIL`, `PHONE`, `SSN`, `CREDIT_CARD`, `IP_ADDRESS`, `DATE`, `ZIP_CODE`.
- `spacy`:
  - Requires `pip install datafog[nlp]`.
  - Useful for unstructured entities like person and organization names.
- `gliner`:
  - Requires `pip install datafog[nlp-advanced]`.
  - Stronger NER coverage than regex for unstructured text.
- `smart`:
  - Cascades regex with optional NER engines.
  - If optional deps are missing, it degrades gracefully and warns.

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
