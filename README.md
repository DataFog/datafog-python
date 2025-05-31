# DataFog: PII Detection & Anonymization

<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo" width="300"></a>
</p>

<p align="center">
  <b>Fast processing • Production-ready • Simple configuration</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/v/datafog.svg?style=flat-square" alt="PyPi Version"></a>
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/pyversions/datafog.svg?style=flat-square" alt="PyPI pyversions"></a>
  <a href="https://github.com/datafog/datafog-python"><img src="https://img.shields.io/github/stars/datafog/datafog-python.svg?style=flat-square&logo=github&label=Stars&logoColor=white" alt="GitHub stars"></a>
  <a href="https://pypistats.org/packages/datafog"><img src="https://img.shields.io/pypi/dm/datafog.svg?style=flat-square" alt="PyPi downloads"></a>
  <a href="https://github.com/datafog/datafog-python/actions/workflows/tests.yml"><img src="https://github.com/datafog/datafog-python/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/datafog/datafog-python/actions/workflows/benchmark.yml"><img src="https://github.com/datafog/datafog-python/actions/workflows/benchmark.yml/badge.svg" alt="Benchmarks"></a>
</p>

---

## Overview

DataFog provides efficient PII detection using a pattern-first approach that processes text significantly faster than traditional NLP methods while maintaining high accuracy.

```python
# Basic usage example
from datafog import DataFog
results = DataFog().scan_text("John's email is john@example.com and SSN is 123-45-6789")
```

### Performance Comparison

| Engine               | 10KB Text Processing | Relative Speed  | Accuracy          |
| -------------------- | -------------------- | --------------- | ----------------- |
| **DataFog (Regex)**  | ~2.4ms               | **190x faster** | High (structured) |
| **DataFog (GLiNER)** | ~15ms                | **32x faster**  | Very High         |
| **DataFog (Smart)**  | ~3-15ms              | **60x faster**  | Highest           |
| spaCy                | ~459ms               | baseline        | Good              |

_Performance measured on 13.3KB business document. GLiNER provides excellent accuracy for named entities while maintaining speed advantage._

### Supported PII Types

| Type             | Examples            | Use Cases              |
| ---------------- | ------------------- | ---------------------- |
| **Email**        | john@company.com    | Contact scrubbing      |
| **Phone**        | (555) 123-4567      | Call log anonymization |
| **SSN**          | 123-45-6789         | HR data protection     |
| **Credit Cards** | 4111-1111-1111-1111 | Payment processing     |
| **IP Addresses** | 192.168.1.1         | Network log cleaning   |
| **Dates**        | 01/01/1990          | Birthdate removal      |
| **ZIP Codes**    | 12345-6789          | Location anonymization |

---

## Quick Start

### Installation

```bash
# Lightweight core (fast regex-based PII detection)
pip install datafog

# With advanced ML models for better accuracy
pip install datafog[nlp]                # spaCy for advanced NLP
pip install datafog[nlp-advanced]       # GLiNER for modern NER
pip install datafog[ocr]                # Image processing with OCR
pip install datafog[all]                # Everything included
```

### Basic Usage

**Detect PII in text:**

```python
from datafog import DataFog

# Simple detection (uses fast regex engine)
detector = DataFog()
text = "Contact John Doe at john.doe@company.com or (555) 123-4567"
results = detector.scan_text(text)
print(results)
# Finds: emails, phone numbers, and more

# Modern NER with GLiNER (requires: pip install datafog[nlp-advanced])
from datafog.services import TextService
gliner_service = TextService(engine="gliner")
result = gliner_service.annotate_text_sync("Dr. John Smith works at General Hospital")
# Detects: PERSON, ORGANIZATION with high accuracy

# Best of both worlds: Smart cascading (recommended for production)
smart_service = TextService(engine="smart")
result = smart_service.annotate_text_sync("Contact john@company.com or call (555) 123-4567")
# Uses regex for structured PII (fast), GLiNER for entities (accurate)
```

**Anonymize on the fly:**

```python
# Redact sensitive data
redacted = DataFog(operations=["scan", "redact"]).process_text(
    "My SSN is 123-45-6789 and email is john@example.com"
)
print(redacted)
# Output: "My SSN is [REDACTED] and email is [REDACTED]"

# Replace with fake data
replaced = DataFog(operations=["scan", "replace"]).process_text(
    "Call me at (555) 123-4567"
)
print(replaced)
# Output: "Call me at [PHONE_A1B2C3]"
```

**Process images with OCR:**

```python
import asyncio
from datafog import DataFog

async def scan_document():
    ocr_scanner = DataFog(operations=["extract", "scan"])
    results = await ocr_scanner.run_ocr_pipeline([
        "https://example.com/document.png"
    ])
    return results

# Extract text and find PII in images
results = asyncio.run(scan_document())
```

---

## Advanced Features

### Engine Selection

Choose the appropriate engine for your needs:

```python
from datafog.services import TextService

# Regex: Fast, pattern-based (recommended for speed)
regex_service = TextService(engine="regex")

# spaCy: Traditional NLP with broad entity recognition
spacy_service = TextService(engine="spacy")

# GLiNER: Modern ML model optimized for NER (requires nlp-advanced extra)
gliner_service = TextService(engine="gliner")

# Smart: Cascading approach - regex → GLiNER → spaCy (best accuracy/speed balance)
smart_service = TextService(engine="smart")

# Auto: Regex → spaCy fallback (legacy)
auto_service = TextService(engine="auto")
```

**Performance & Accuracy Guide:**

| Engine   | Speed       | Accuracy | Use Case                        | Install Requirements                |
| -------- | ----------- | -------- | ------------------------------- | ----------------------------------- |
| `regex`  | 🚀 Fastest  | Good     | Structured PII (emails, phones) | Core only                           |
| `gliner` | ⚡ Fast     | Better   | Modern NER, custom entities     | `pip install datafog[nlp-advanced]` |
| `spacy`  | 🐌 Slower   | Good     | Traditional NLP entities        | `pip install datafog[nlp]`          |
| `smart`  | ⚡ Balanced | Best     | Combines all approaches         | `pip install datafog[nlp-advanced]` |

**Model Management:**

```python
# Download specific GLiNER models
import subprocess

# PII-specialized model (recommended)
subprocess.run(["datafog", "download-model", "urchade/gliner_multi_pii-v1", "--engine", "gliner"])

# General-purpose model
subprocess.run(["datafog", "download-model", "urchade/gliner_base", "--engine", "gliner"])

# List available models
subprocess.run(["datafog", "list-models", "--engine", "gliner"])
```

### Anonymization Options

```python
from datafog import DataFog
from datafog.models.anonymizer import AnonymizerType, HashType

# Hash with different algorithms
hasher = DataFog(
    operations=["scan", "hash"],
    hash_type=HashType.SHA256  # or MD5, SHA3_256
)

# Target specific entity types only
selective = DataFog(
    operations=["scan", "redact"],
    entities=["EMAIL", "PHONE"]  # Only process these types
)
```

### Batch Processing

```python
documents = [
    "Document 1 with PII...",
    "Document 2 with more data...",
    "Document 3..."
]

# Process multiple documents efficiently
results = DataFog().batch_process(documents)
```

---

## Performance Benchmarks

Performance comparison with alternatives:

### Speed Comparison (10KB text)

```
DataFog Pattern:  4ms   ████████████████████████████████ 123x faster
spaCy:         480ms   ██ baseline
```

### Engine Selection Guide

| Scenario                   | Recommended Engine | Why                                   |
| -------------------------- | ------------------ | ------------------------------------- |
| **High-volume processing** | `pattern`          | Maximum speed, consistent performance |
| **Unknown entity types**   | `spacy`            | Broader entity recognition            |
| **General purpose**        | `auto`             | Smart fallback, best of both worlds   |
| **Real-time applications** | `pattern`          | Sub-millisecond processing            |

---

## CLI Usage

DataFog includes a command-line interface:

```bash
# Scan text for PII
datafog scan-text "John's email is john@example.com"

# Process images
datafog scan-image document.png --operations extract,scan

# Anonymize data
datafog redact-text "My phone is (555) 123-4567"
datafog replace-text "SSN: 123-45-6789"
datafog hash-text "Email: john@company.com" --hash-type sha256

# Utility commands
datafog health
datafog list-entities
datafog show-config
```

---

## Features

### Security & Compliance

- Detection of regulated data types for GDPR/CCPA compliance
- Audit trails for tracking detection and anonymization
- Configurable detection thresholds

### Scalability

- Batch processing for handling multiple documents
- Memory-efficient processing for large files
- Async support for non-blocking operations

### Integration Example

```python
# FastAPI middleware example
from fastapi import FastAPI
from datafog import DataFog

app = FastAPI()
detector = DataFog()

@app.middleware("http")
async def redact_pii_middleware(request, call_next):
    # Automatically scan/redact request data
    pass
```

---

## Common Use Cases

### Enterprise

- Log sanitization
- Data migration with PII handling
- Compliance reporting and audits

### Data Science

- Dataset preparation and anonymization
- Privacy-preserving analytics
- Research compliance

### Development

- Test data generation
- Code review for PII detection
- API security validation

---

## Installation & Setup

### Basic Installation

```bash
pip install datafog
```

### Development Setup

```bash
git clone https://github.com/datafog/datafog-python
cd datafog-python
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
just setup
```

### Docker Usage

```dockerfile
FROM python:3.10-slim
RUN pip install datafog
COPY . .
CMD ["python", "your_script.py"]
```

---

## Contributing

Contributions are welcome in the form of:

- Bug reports
- Feature requests
- Documentation improvements
- New pattern patterns for PII detection
- Performance improvements

### Quick Contribution Guide

```bash
# Setup development environment
git clone https://github.com/datafog/datafog-python
cd datafog-python
just setup

# Run tests
just test

# Format code
just format

# Submit PR
git checkout -b feature/your-improvement
# Make your changes
git commit -m "Add your improvement"
git push origin feature/your-improvement
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Benchmarking & Performance

### Run Benchmarks Locally

```bash
# Install benchmark dependencies
pip install pytest-benchmark

# Run performance tests
pytest tests/benchmark_text_service.py -v

# Compare with baseline
python scripts/run_benchmark_locally.sh
```

### Continuous Performance Monitoring

Our CI pipeline:

- Runs benchmarks on every PR
- Compares against baseline performance
- Fails builds if performance degrades >10%
- Tracks performance trends over time

---

## Documentation & Support

| Resource              | Link                                                                        |
| --------------------- | --------------------------------------------------------------------------- |
| **Documentation**     | [docs.datafog.ai](https://docs.datafog.ai)                                  |
| **Community Discord** | [Join here](https://discord.gg/bzDth394R4)                                  |
| **Bug Reports**       | [GitHub Issues](https://github.com/datafog/datafog-python/issues)           |
| **Feature Requests**  | [GitHub Discussions](https://github.com/datafog/datafog-python/discussions) |
| **Support**           | [hi@datafog.ai](mailto:hi@datafog.ai)                                       |

---

## License & Acknowledgments

DataFog is released under the [MIT License](LICENSE).

**Built with:**

- Pattern optimization for efficient processing
- spaCy integration for NLP capabilities
- Tesseract & Donut for OCR capabilities
- Pydantic for data validation

---

[GitHub](https://github.com/datafog/datafog-python) • [Documentation](https://docs.datafog.ai) • [Discord](https://discord.gg/bzDth394R4)
