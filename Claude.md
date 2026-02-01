# DataFog - Claude Development Guide

## Project Overview
**DataFog** is an open-source Python library for PII detection and anonymization with a focus on speed and lightweight architecture.

## Core Value Proposition
- **Ultra-Fast Performance**: 190x faster than spaCy for structured PII, 32x faster with GLiNER
- **Lightweight Core**: <2MB package with optional ML extras
- **Modern Engine Options**: Regex, GLiNER, spaCy, and smart cascading
- **Production Ready**: Comprehensive testing, CI/CD, and performance validation

## Current Project Status
**Version: 4.3.0**

### ✅ Recently Completed (Latest)
- **GLiNER Integration**: Modern NER engine with PII-specialized models
- **Smart Cascading**: Intelligent regex → GLiNER → spaCy progression
- **Enhanced CLI**: Model management with `--engine` flags
- **Performance Validation**: 190x regex, 32x GLiNER benchmarks confirmed
- **CI/CD Consolidation**: 7 workflows → 3 (ci, release, benchmark)

## Quick Development Setup

```bash
# 1. Clone and setup environment
git clone https://github.com/datafog/datafog-python.git
cd datafog-python
python -m venv .venv && source .venv/bin/activate

# 2. Install with dev dependencies
pip install -e ".[dev]" && pip install -r requirements-dev.txt
pre-commit install

# 3. Install ML extras for advanced features
pip install -e ".[nlp]"           # spaCy
pip install -e ".[nlp-advanced]"  # GLiNER (NEW)
pip install -e ".[all]"           # Everything

# 4. Verify installation
python -c "from datafog.services.text_service import TextService; print('✅ All engines:', ['regex', 'gliner', 'spacy', 'smart', 'auto'])"
```

## Architecture Overview

### Engine Ecosystem (Updated with GLiNER)
```python
from datafog.services.text_service import TextService

# Core engines (always available)
regex_service = TextService(engine="regex")      # 190x faster, structured PII

# ML engines (require extras)
gliner_service = TextService(engine="gliner")    # 32x faster, modern NER
spacy_service = TextService(engine="spacy")      # Comprehensive NLP

# Smart combinations
smart_service = TextService(engine="smart")      # Cascading: regex→GLiNER→spaCy
auto_service = TextService(engine="auto")        # Legacy: regex→spaCy
```

### Performance Comparison (Validated)
| Engine  | Speed vs spaCy | Accuracy | Use Case | Install |
|---------|----------------|----------|----------|---------|
| `regex` | **190x faster** | High (structured) | Emails, phones, SSNs | Core only |
| `gliner` | **32x faster** | Very High | Modern NER, custom entities | `[nlp-advanced]` |
| `spacy` | 1x (baseline) | Good | Traditional NLP | `[nlp]` |
| `smart` | **60x faster** | Highest | Best balance | `[nlp-advanced]` |

### Dependency Strategy
```python
# Lightweight core (<2MB)
pip install datafog

# Optional ML engines
pip install datafog[nlp]           # spaCy (traditional NLP)
pip install datafog[nlp-advanced]  # GLiNER (modern NER) 
pip install datafog[ocr]           # Image processing
pip install datafog[all]           # Everything
```

## GLiNER Integration (NEW)

### Overview
GLiNER (Generalist Model for Named Entity Recognition) provides modern, accurate NER capabilities optimized for PII detection.

### Key Features
- **PII-Specialized Models**: `urchade/gliner_multi_pii-v1` trained specifically for PII
- **Custom Entity Types**: Configurable entity detection beyond default PII types
- **Smart Cascading**: Automatically tries regex first, GLiNER second, spaCy last
- **CLI Management**: Download and manage GLiNER models via CLI

### Usage Examples
```python
# GLiNER engine
from datafog.services.text_service import TextService
service = TextService(engine="gliner", gliner_model="urchade/gliner_multi_pii-v1")
result = service.annotate_text_sync("Dr. John Doe at john@hospital.org")
# Detects: PERSON, EMAIL, and more

# Smart cascading (recommended)
smart_service = TextService(engine="smart")
result = smart_service.annotate_text_sync(text)
# Uses regex for speed, GLiNER for accuracy, spaCy as fallback

# CLI model management
subprocess.run(["datafog", "download-model", "urchade/gliner_base", "--engine", "gliner"])
subprocess.run(["datafog", "list-models", "--engine", "gliner"])
```

### Available GLiNER Models
- `urchade/gliner_multi_pii-v1` - PII-specialized (recommended)
- `urchade/gliner_base` - General purpose starter
- `urchade/gliner_large-v2` - Higher accuracy
- `knowledgator/modern-gliner-bi-large-v1.0` - 4x more efficient

## Development Workflow

### Git Branch Strategy
- **main**: Production releases only
- **dev**: Main development branch (use this)
- **feature/***: New features from dev
- **fix/***: Bug fixes from dev

### Making Changes
```bash
# Start from dev
git checkout dev && git pull origin dev

# Create feature branch  
git checkout -b feature/your-change

# Make changes, test, commit
git add . && git commit -m "feat(engine): description"

# Push and create PR to dev (not main!)
git push -u origin feature/your-change
```

### Testing
```bash
# Run specific test suites
pytest tests/test_text_service.py -v           # Core functionality
pytest tests/test_gliner_annotator.py -v      # GLiNER integration
pytest tests/benchmark_text_service.py -v     # Performance validation

# Integration testing
pytest -m integration                          # Real services
PYTEST_DONUT=yes pytest tests/test_ocr_integration.py  # OCR with real models

# Performance requirements
# - Regex: 150x+ faster than spaCy
# - GLiNER: 25x+ faster than spaCy  
# - Package size: Core <2MB, full <8MB
```

## Key Implementation Patterns

### Simple API (Recommended)
```python
# Always available, lightweight
from datafog import detect, process
entities = detect("john@example.com")
result = process("john@example.com", method="redact")
```

### Advanced Engine Selection
```python
# For specialized use cases
from datafog.services.text_service import TextService

# High-speed structured PII
service = TextService(engine="regex")

# Modern NER with custom entities
service = TextService(
    engine="gliner", 
    gliner_model="urchade/gliner_base"
)

# Best overall accuracy/speed balance
service = TextService(engine="smart")
```

### Graceful Degradation
```python
# Handles missing dependencies elegantly
try:
    service = TextService(engine="gliner")
except ImportError:
    print("GLiNER not available, falling back to regex")
    service = TextService(engine="regex")
```

## Common Tasks

### Adding New Entity Types
1. Update regex patterns in `regex_annotator.py`
2. Add GLiNER entity types in `gliner_annotator.py`
3. Update tests and benchmarks
4. Validate performance doesn't regress >10%

### Performance Optimization
1. Profile with existing benchmarks
2. Maintain speed thresholds (regex 150x+, GLiNER 25x+)
3. Update baselines when making improvements
4. Test across all engines

### CLI Enhancements
1. Update `client.py` with new commands
2. Support `--engine` flag for multi-engine commands
3. Add comprehensive help text and examples
4. Test both spaCy and GLiNER variants

## CI/CD & Release Process

### Workflow Architecture (3 workflows)

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `ci.yml` | Lint + Test + Coverage + Wheel size | Push/PR to main/dev |
| `release.yml` | Alpha/Beta/Stable publishing | Schedule + manual dispatch |
| `benchmark.yml` | Performance benchmarks | Push/PR/weekly |

### Release Cadence
- **Alpha** (Mon-Wed 2AM UTC): Automatic from `dev`, date+commit versioning
- **Beta** (Thursday 2AM UTC): Automatic from `dev`, incremental beta numbers
- **Stable** (manual dispatch): From `main`, base version or override

### Release Pipeline
`determine-release` → `test` → `publish` → `cleanup`
- Tests are a hard gate — no tests = no publish
- Stable releases check out `main`; alpha/beta check out `dev`
- Old alphas pruned to 7, betas to 5
- `[skip ci]` in version bump commits to prevent loops

### Pre-commit Hooks
- **isort**, **black**, **flake8**, **ruff**: Code formatting and linting
- **prettier**: Markdown, JSON, YAML formatting
- **gitleaks**: Secret scanning
- **pre-commit-hooks**: Large file checks, merge conflict detection, YAML validation

## Environment Variables
```bash
# Testing configuration
export PYTEST_DONUT=yes              # Enable real OCR testing
export DATAFOG_LOG_LEVEL=DEBUG       # Verbose logging

# Development helpers
export PYTHONPATH=$(pwd)             # Local development imports
```

## Performance Requirements
- **Core Package**: <2MB (from ~8MB in v4.0.x)
- **Regex Engine**: 150x+ faster than spaCy (currently 190x)
- **GLiNER Engine**: 25x+ faster than spaCy (currently 32x)  
- **Memory Usage**: Graceful handling of large texts (1MB+ chunks)
- **Model Loading**: Cache GLiNER models to avoid repeated downloads

## Best Practices for Claude Agents

Before beginning any task please checkout a branch from `dev` and create a pull request to `dev`.

### Code Quality
- Follow existing patterns before implementing new approaches
- Add comprehensive tests for all new functionality
- Update documentation immediately with code changes
- Run benchmarks for any text processing modifications

### GLiNER Development
- Use PII-specialized models when available (`urchade/gliner_multi_pii-v1`)
- Test graceful degradation when GLiNER dependencies missing
- Validate smart cascading thresholds with real data
- Consider model download time and caching strategies

### Release Preparation
- Alpha/beta releases are automated via `release.yml` schedule
- Stable releases: merge `dev` → `main`, then trigger `release.yml` with `stable` type
- Use `dry_run: true` to validate before actual publish
- Performance validation on realistic data sets
- In Release Notes or Comments, do not reference that it was authored by Claude (all code is anonymously authored)

This guide provides the essential information for DataFog development while maintaining focus on current priorities and recent GLiNER integration work.