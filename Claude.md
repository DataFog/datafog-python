# DataFog - Claude Development Guide

## Project Overview
**DataFog** is an open-source Python library for PII detection and anonymization with a focus on speed and lightweight architecture.

## Core Value Proposition
- **Ultra-Fast Performance**: 190x faster than spaCy for structured PII, 32x faster with GLiNER
- **Lightweight Core**: <2MB package with optional ML extras
- **Modern Engine Options**: Regex, GLiNER, spaCy, and smart cascading
- **Production Ready**: Comprehensive testing, CI/CD, and performance validation

## Current Project Status
**Version: 4.1.1** → **Targeting 4.2.0** with GLiNER integration

### ✅ Recently Completed (Latest)
- **GLiNER Integration**: Modern NER engine with PII-specialized models
- **Smart Cascading**: Intelligent regex → GLiNER → spaCy progression  
- **Enhanced CLI**: Model management with `--engine` flags
- **Performance Validation**: 190x regex, 32x GLiNER benchmarks confirmed
- **Comprehensive Testing**: 87% pass rate (156/180 tests)

### 🎯 Current Focus (v4.2.0)
- **Final test cleanup**: Address remaining test failures
- **GLiNER refinement**: Optimize cascading thresholds
- **Documentation polish**: Update all GLiNER references
- **Release preparation**: Version bump and changelog

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

### Automated Validation
- **Tests**: Python 3.10-3.12 across all platforms
- **Performance**: Regression detection with 10% threshold
- **Package Size**: <2MB core, <8MB full enforcement
- **Pre-commit**: Code formatting and linting

### Release Workflow
1. **Feature complete**: All planned changes implemented
2. **Tests passing**: Full CI green across all platforms  
3. **Performance validated**: No regression in benchmarks
4. **Documentation updated**: README, CHANGELOG, examples current
5. **Version bump**: Update `__about__.py` and `setup.py`
6. **Release tag**: Deploy via GitHub Actions

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
- Feature freeze by Thursday for Friday releases
- Performance validation on realistic data sets
- Cross-platform testing (Linux, macOS, Windows)
- Community-facing documentation and examples
- In Release Notes or Comments, do not reference that it was sauthored by Claude (all code is anonymously authored)

This guide provides the essential information for DataFog development while maintaining focus on current priorities and recent GLiNER integration work.