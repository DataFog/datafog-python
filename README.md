# DataFog Python

[![PyPI version](https://img.shields.io/pypi/v/datafog)](https://pypi.org/project/datafog/)
[![Python versions](https://img.shields.io/pypi/pyversions/datafog)](https://pypi.org/project/datafog/)
[![CI](https://github.com/DataFog/datafog-python/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/DataFog/datafog-python/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DataFog/datafog-python/branch/dev/graph/badge.svg)](https://codecov.io/gh/DataFog/datafog-python)
[![License](https://img.shields.io/github/license/DataFog/datafog-python)](LICENSE)

Python SDK for PII detection and redaction in text and images, combining regex and NLP pipelines for production privacy workflows.

- Website: https://www.datafog.ai
- Docs: https://docs.datafog.ai
- PyPI: https://pypi.org/project/datafog/
- Discord: https://discord.gg/bzDth394R4

## Installation

```bash
# Core install (regex engine only)
pip install datafog

# Add spaCy support
pip install "datafog[nlp]"

# Add advanced NER support (GLiNER + dependencies)
pip install "datafog[nlp-advanced]"

# Full feature set
pip install "datafog[all]"
```

## Quick Start

```python
import datafog

text = "Contact john@example.com or call (555) 123-4567"

# One-liner redaction
print(datafog.sanitize(text, engine="regex"))
# Contact [EMAIL_1] or call [PHONE_1]

# Scan first, then choose handling strategy
scan = datafog.scan_prompt("My SSN is 123-45-6789", engine="regex")
print(len(scan.entities))
```

## LLM Guardrail API

```python
import datafog

guard = datafog.create_guardrail(engine="regex", on_detect="redact")

@guard
def call_llm() -> str:
    return "Email admin@example.com"

print(call_llm())
# Email [EMAIL_1]
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

## Engines

- `regex`: fastest, zero extra dependencies, strong for structured PII.
- `spacy`: install with `datafog[nlp]` for better unstructured entity detection.
- `gliner`: install with `datafog[nlp-advanced]` for stronger NER coverage.
- `smart`: cascades regex with optional NER engines and degrades gracefully.

## Compatibility APIs

```python
from datafog import DataFog
from datafog.services import TextService

print(DataFog().scan_text("Email john@example.com"))
print(TextService(engine="regex").annotate_text_sync("Call (555) 123-4567"))
```

## Release Channels

Current release workflow is branch-based:

- `dev`: active development and prerelease flow (alpha/beta).
- `main`: stable release source branch.

For stable publishes, release automation targets `main`.

## Telemetry

DataFog collects anonymous telemetry by default. Input text and detected PII values are not sent.

To opt out:

```bash
export DATAFOG_NO_TELEMETRY=1
# or
export DO_NOT_TRACK=1
```

## Development

```bash
git clone https://github.com/DataFog/datafog-python
cd datafog-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all,dev]"
pytest tests/
```
