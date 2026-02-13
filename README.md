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

DataFog includes anonymous telemetry by default.

To opt out:

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
pytest tests/
```
