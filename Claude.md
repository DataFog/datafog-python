# DataFog - Claude Development Guide

## Project Overview
**DataFog** is an open-source Python library for PII (Personally Identifiable Information) detection and anonymization of unstructured data. It provides both CLI tools and Python SDK for scanning, redacting, replacing, and hashing sensitive information in text and images.

## Core Value Proposition
- **Fast Regex Engine**: 190x faster than spaCy for structured PII detection (validated May 2025)
- **Lightweight Architecture**: Core package <2MB with optional extras for specific functionality
- **Simple API**: Easy-to-use `detect()` and `process()` functions for quick PII detection
- **Intelligent Engine Selection**: Auto mode tries regex first, falls back to spaCy for complex entities
- **OCR Capabilities**: Extract and process PII from images using Tesseract or Donut (optional extra)
- **Multiple Anonymization Options**: Redact, replace, or hash detected PII
- **Production Ready**: Comprehensive test suite, CI/CD, and performance benchmarks

## Current Project Status
**Version: 4.1.0** - Production ready with lightweight architecture

### ✅ Completed v4.1.0 Features (Stories 1.1-1.10)
- **Regex Annotator**: High-performance PII detection engine (190x faster than spaCy)
- **Engine Selection**: Auto/regex/spaCy modes with intelligent fallback
- **Dependency Splitting**: Lightweight core (<2MB) with optional extras (nlp, ocr, distributed, etc.)
- **Simple API**: Easy-to-use `detect()` and `process()` functions for quick PII detection
- **Performance Benchmarks**: Comprehensive validation with defensible 190x speed claims
- **Integration Tests**: Real Spark, CLI smoke tests, OCR testing with flags
- **Streamlined CI/CD**: Unified workflows with automatic pre-commit integration
- **Package Optimization**: Core install reduced from ~8MB to <2MB
- **Graceful Degradation**: Smart imports with helpful error messages for missing extras
- **Fair Benchmark Analysis**: Independent performance validation scripts

### ✅ Critical Bug Fixes Resolved (May 2025)
- **CI/CD Stability**: Fixed GitHub Actions failures while preserving lean architecture
- **Structured Output Bug**: Resolved multi-chunk text processing in TextService
- **Test Suite Health**: Improved from 33% to 87% test success rate (156/180 passing)
- **Conditional Testing**: Updated test architecture for lean vs full dependency testing
- **Mock Fixtures**: Corrected service patching for proper CI validation
- **Anonymizer Integration**: Fixed AnnotationResult format conversion for regex engine
- **Benchmark Validation**: Original performance tests now passing consistently

### 🚧 Current Focus Areas
- **Final Test Cleanup**: Address remaining 23 issues in text_service.py and cli_smoke.py
- **Release Finalization**: Final testing and version tagging for 4.1.0 stable
- **Performance Monitoring**: Continuous benchmarking in CI

## Development Environment Setup

### Prerequisites
- **Python**: 3.10, 3.11, or 3.12 supported
- **Git**: Latest version
- **Optional System Dependencies**: 
  - Tesseract OCR (`tesseract-ocr`, `libtesseract-dev` on Ubuntu) - only for OCR extras
  - Java (for PySpark functionality) - only for distributed extras

### Quick Start
```bash
# 1. Clone and setup
git clone https://github.com/datafog/datafog-python.git
cd datafog-python

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# 3. Install lightweight core for development
pip install -e ".[dev]"
pip install -r requirements-dev.txt

# 4. Set up pre-commit hooks (IMPORTANT!)
pre-commit install

# 5. Verify installation (lightweight core)
python -c "from datafog import detect; print('Core works:', detect('test@example.com'))"

# 6. Install optional extras as needed
pip install -e ".[nlp]"      # For spaCy integration
pip install -e ".[ocr]"      # For image processing
pip install -e ".[all]"      # For full functionality

# 7. Run tests to ensure everything works
just test
```

### Development Tools
```bash
# Format code
just format

# Lint code
just lint

# Run tests with coverage
just coverage-html

# Run benchmarks
pytest tests/benchmark_text_service.py -v

# Run integration tests
pytest -m integration

# Check wheel size
python scripts/check_wheel_size.py
```

## Git Development Workflow

### Branch Structure
- **main**: Production releases, protected branch
- **dev**: Main development branch, all features merge here
- **feature/***: Individual feature branches from dev
- **fix/***: Bug fix branches from dev
- **hotfix/***: Emergency fixes from main

### Workflow for Claude Code Agents

**IMPORTANT**: Always start from the `dev` branch, never from `main`.

```bash
# 1. Always start from dev
git checkout dev
git pull origin dev

# 2. Create feature branch
git checkout -b feature/your-feature-name
# Examples:
# git checkout -b feature/add-new-entity-type
# git checkout -b fix/memory-leak-in-chunking
# git checkout -b docs/update-performance-guide

# 3. Make changes and commit
git add .
git commit -m "feat(regex): add support for passport numbers"

# 4. Push branch
git push -u origin feature/your-feature-name

# 5. Create PR to dev branch (not main!)
# Target: dev ← Source: feature/your-feature-name

# 6. After merge, cleanup
git checkout dev
git pull origin dev
git branch -d feature/your-feature-name
```

### Commit Message Format
Use conventional commits for automated changelog generation:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Common Types for DataFog:
- **feat**: New features (`feat(regex): add email validation`)
- **fix**: Bug fixes (`fix(spacy): resolve memory leak in chunking`)
- **perf**: Performance improvements (`perf(regex): optimize email pattern`)
- **docs**: Documentation (`docs: update engine selection guide`)
- **test**: Test changes (`test: add benchmarks for new entities`)
- **refactor**: Code restructuring (`refactor(text): extract common utilities`)
- **style**: Code formatting (`style: fix flake8 warnings`)
- **chore**: Maintenance (`chore(deps): update spacy to 3.7.6`)

#### Scopes for DataFog:
- `(regex)` - Regex annotator engine
- `(spacy)` - SpaCy integration
- `(text)` - Text processing services
- `(image)` - Image/OCR processing
- `(cli)` - Command line interface
- `(api)` - API endpoints and models
- `(spark)` - PySpark integration
- `(anonymizer)` - Anonymization functionality
- `(tests)` - Test infrastructure
- `(ci)` - CI/CD and automation
- `(docs)` - Documentation

## Architecture Overview

### Lightweight Core Architecture (v4.1.0)
```
datafog/
├── __init__.py          # Simple API: detect(), process()
├── main.py              # Lightweight DataFog class (regex-only core)
├── client.py            # CLI interface
├── config.py            # Configuration and enums
├── models/              # Data models (Pydantic)
│   ├── annotator.py     # Annotation results
│   ├── anonymizer.py    # Anonymization models
│   └── common.py        # Shared models
├── services/            # Core business logic
│   ├── text_service.py  # Smart engine selection with graceful degradation
│   ├── image_service.py # OCR processing (requires ocr extra)
│   └── spark_service.py # Distributed processing (requires distributed extra)
└── processing/          # Processing engines
    ├── text_processing/
    │   ├── regex_annotator/     # Core: Always available
    │   └── spacy_pii_annotator.py # Optional: Requires nlp extra
    └── image_processing/        # Optional: Requires ocr extra
        ├── donut_processor.py
        └── pytesseract_processor.py
```

### Dependency Splitting Strategy
```python
# Core install (lightweight, <2MB)
pip install datafog

# Optional extras for specific functionality
pip install datafog[nlp]         # Adds spaCy for advanced NLP
pip install datafog[ocr]         # Adds Tesseract/Donut for images
pip install datafog[distributed] # Adds PySpark for big data
pip install datafog[web]         # Adds web service dependencies
pip install datafog[cli]         # Adds CLI enhancements
pip install datafog[crypto]      # Adds advanced hashing
pip install datafog[all]         # Includes all functionality
```

### Engine Selection Logic
```python
# Simple API (always available, lightweight core)
from datafog import detect, process
entities = detect("Contact john@example.com")         # Fast regex detection
result = process("Contact john@example.com", "redact") # Fast anonymization

# Advanced TextService (requires appropriate extras)
from datafog.services.text_service import TextService
service = TextService(engine="regex")   # Fast pattern matching (core)
service = TextService(engine="spacy")   # Advanced NLP (requires nlp extra)
service = TextService(engine="auto")    # Smart selection (requires nlp extra)

# Auto mode strategy (when nlp extra installed):
# 1. Try regex first (fast)
# 2. If no entities found, fallback to spaCy (comprehensive)
# 3. Return results from whichever engine found entities
```

### Supported Entity Types
**Regex Engine** (Fast, structured data):
- EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS, DOB, ZIP

**SpaCy Engine** (NLP-based, unstructured data):
- PERSON, ORG, GPE, CARDINAL, FAC, DATE, TIME, etc.

## Performance Validation & Benchmarking

### Fair Benchmark Analysis (May 2025)

A comprehensive benchmarking initiative was completed to validate DataFog's performance claims with rigorous, defensible methodology. The analysis updated the marketing claim from "123x faster" to **"190x faster than spaCy"** based on unbiased testing.

#### Key Deliverables
- **`scripts/fair_benchmark.py`**: Independent benchmark script using minimal dependencies
- **`scripts/benchmark_analysis_report.md`**: Comprehensive analysis with marketing recommendations
- **Updated performance baselines**: 190x speedup validated across multiple test runs

#### Methodology Highlights
- **Clean Environment**: Isolated test environment with only spaCy + Pydantic dependencies
- **Identical Test Data**: 13.3KB realistic business document with various PII types
- **Multiple Runs**: 5 measured runs per engine (excluding warmup) for statistical reliability
- **Fair Comparison**: Both engines processed identical text samples under identical conditions

#### Validated Results
- **Regex Engine**: 2.4ms average processing time, 5,502 KB/s throughput
- **SpaCy Engine**: 459ms average processing time, 29 KB/s throughput
- **Performance Ratio**: 190-195x faster (consistent across multiple runs)
- **Entity Detection**: Regex found 190 structured PII entities, spaCy found 550 contextual entities

#### Business Impact
- **Accurate Marketing Claims**: Defensible 190x performance advantage
- **Cost Efficiency**: Significant infrastructure cost savings due to lower resource requirements
- **Scalability**: Linear performance scaling for enterprise workloads
- **No Model Dependencies**: Instant startup without large ML model downloads

#### Technical Validation
- **Consistency**: ±2% variance across multiple test runs
- **Existing Benchmarks**: Confirmed similar patterns (97x speedup in pytest benchmarks)
- **Real-world Applicability**: Testing on realistic business document formats
- **Precision Analysis**: Regex excels at structured PII, spaCy at contextual entity detection

This benchmarking work provides the foundation for confident performance marketing and establishes DataFog's quantified competitive advantages in the PII detection market.

## CI/CD Workflow Architecture

### Streamlined GitHub Actions (May 2025)

The GitHub Actions workflows were comprehensively refactored to eliminate redundancy and improve developer experience. The new architecture provides unified, efficient CI/CD with automatic pre-commit integration.

#### Current Workflow Structure
```
.github/workflows/
├── ci.yml                    # Unified CI for all branches
├── pre-commit-auto-fix.yml   # Auto-fix formatting on PRs
├── benchmark.yml             # Performance monitoring
├── wheel_size.yml            # Package size validation
└── publish-pypi.yml          # Release automation
```

#### Key Improvements
- **Eliminated Redundancy**: Reduced from 9 overlapping workflows to 5 focused workflows
- **Unified CI**: Single `ci.yml` handles pre-commit, tests (Python 3.10-3.12), and wheel size checks
- **Auto-fix Pre-commit**: PRs automatically get formatting fixes applied
- **Consistent Versions**: All workflows use latest action versions (checkout@v4, setup-python@v5)
- **Better Error Messages**: Clear feedback when pre-commit or other checks fail

#### Pre-commit Integration
The workflow now seamlessly integrates pre-commit hooks:

1. **Local Development**: `pre-commit install` runs hooks before each commit
2. **GitHub CI**: `ci.yml` runs pre-commit checks on all branches
3. **Auto-fix PRs**: `pre-commit-auto-fix.yml` automatically fixes formatting issues
4. **Clear Guidance**: Setup instructions and troubleshooting in this document

#### Workflow Triggers
- **`ci.yml`**: Runs on all pushes to main/dev/feature/fix/chore branches and PRs to main/dev
- **`pre-commit-auto-fix.yml`**: Runs on PR creation and updates
- **`benchmark.yml`**: Runs on main/dev changes and weekly schedule
- **`wheel_size.yml`**: Runs on main/dev changes to enforce 8MB limit
- **`publish-pypi.yml`**: Manual releases and automatic beta releases from dev

This architecture ensures comprehensive testing while minimizing CI/CD overhead and providing excellent developer experience.

## Parallel Development Tasks

### Terminal 1: Core Engine Development
**Focus**: Text processing engines and performance
```bash
git checkout dev
git checkout -b feature/engine-improvements

# Tasks:
# - Optimize regex patterns
# - Add new entity types  
# - Improve spaCy integration
# - Performance tuning
```

### Terminal 2: API & Models
**Focus**: Data models, API interfaces, and validation
```bash
git checkout dev  
git checkout -b feature/api-enhancements

# Tasks:
# - Add new Pydantic models
# - Extend anonymization options
# - Improve error handling
# - API documentation
```

### Terminal 3: CLI & User Experience
**Focus**: Command-line interface and user-facing features
```bash
git checkout dev
git checkout -b feature/cli-improvements

# Tasks:
# - Add new CLI commands
# - Improve error messages
# - Add progress indicators
# - Help documentation
```

### Terminal 4: Testing & Quality
**Focus**: Test coverage, CI/CD, and quality assurance
```bash
git checkout dev
git checkout -b feature/test-improvements

# Tasks:
# - Add integration tests
# - Improve benchmark coverage
# - CI/CD enhancements
# - Documentation tests
```

### Terminal 5: Image Processing & OCR
**Focus**: Image handling and OCR capabilities
```bash
git checkout dev
git checkout -b feature/ocr-enhancements

# Tasks:
# - Improve OCR accuracy
# - Add image preprocessing
# - Support new image formats
# - OCR performance optimization
```

## Testing Strategy

### Test Categories
```bash
# Unit tests (fast)
pytest tests/ -v

# Integration tests (slower, real services)
pytest -m integration

# Benchmarks (performance monitoring)
pytest tests/benchmark_text_service.py --benchmark-autosave

# OCR tests (requires PYTEST_DONUT=yes for real OCR)
PYTEST_DONUT=yes pytest tests/test_ocr_integration.py

# CLI smoke tests
pytest tests/test_cli_smoke.py -v
```

### Test Guidelines
- **Unit tests**: Mock external dependencies, focus on logic
- **Integration tests**: Use real services (Spark local mode, actual OCR)
- **Benchmarks**: Ensure regex stays 150x+ faster than spaCy (validated at 190x)
- **Dependency tests**: Verify graceful degradation when extras not installed
- **Package size tests**: Enforce <2MB core, <8MB with all extras
- **CI tests**: Must pass before any merge to dev

### Performance Requirements
- **Regex engine**: Must process 10KB text in <200μs (currently ~2.4ms)
- **Core package size**: Keep under 2MB (down from ~8MB in v4.0.x)
- **Performance advantage**: Maintain 150x+ speedup over spaCy (currently 190x validated)
- **Regression threshold**: Performance cannot degrade >10% from baseline

## Key Implementation Patterns

### Simple API Pattern (Recommended for most users)
```python
# Lightweight core functions (always available)
from datafog import detect, process

# Fast PII detection
entities = detect("Contact john@example.com at (555) 123-4567")
# Returns: [{'type': 'EMAIL', 'value': 'john@example.com', 'start': 8, 'end': 24}, ...]

# Quick anonymization
result = process("Contact john@example.com", anonymization_method="redact")
# Returns: "Contact [EMAIL_REDACTED]"
```

### Advanced Engine Selection Pattern
```python
# Full TextService (requires appropriate extras)
from datafog.services.text_service import TextService

# For high-performance structured PII (core only)
service = TextService(engine="regex")
result = service.annotate_text_sync(text)

# For comprehensive entity detection (requires nlp extra)
service = TextService(engine="spacy") 
result = service.annotate_text_sync(text)

# For intelligent auto-selection (requires nlp extra)
service = TextService(engine="auto")  # defaults to regex if nlp not available
result = service.annotate_text_sync(text)
```

### Anonymization Pattern
```python
from datafog.models.anonymizer import Anonymizer, AnonymizerType, HashType

# Different anonymization strategies
anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REDACT)
anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REPLACE)
anonymizer = Anonymizer(
    anonymizer_type=AnonymizerType.HASH, 
    hash_type=HashType.SHA256
)

result = anonymizer.anonymize(text, annotations)
```

### Structured Output Pattern
```python
# Get structured span objects instead of dictionaries
result = service.annotate_text_sync(text, structured=True)
for span in result:
    print(f"{span.label}: {span.text} at {span.start}-{span.end}")
```

## Common Development Tasks

### Adding a New Entity Type
1. **Update regex patterns** in `regex_annotator.py`
2. **Add test cases** in `test_regex_annotator.py`
3. **Update documentation** with new entity type
4. **Add benchmarks** if significant performance impact

### Performance Optimization
1. **Profile first**: Use benchmarks to identify bottlenecks
2. **Measure impact**: Run before/after benchmarks
3. **Maintain thresholds**: Ensure no regression >10%
4. **Update baselines**: When making intentional improvements

### Adding CLI Commands
1. **Extend client.py** with new Typer commands
2. **Add tests** in `test_client.py` and `test_cli_smoke.py`
3. **Update help documentation**
4. **Add examples** to README

### Debugging Guidelines
```bash
# Enable verbose logging
export DATAFOG_LOG_LEVEL=DEBUG

# Run single test with output
pytest tests/test_specific.py -v -s

# Debug OCR issues
PYTEST_DONUT=yes pytest tests/test_ocr_integration.py -v -s

# Profile performance
python -m cProfile -o profile.out scripts/benchmark_script.py
```

## CI/CD Integration

### GitHub Actions Workflows (Streamlined May 2025)
- **Unified CI**: Single workflow for pre-commit, tests, and wheel size checks
- **Auto-fix PRs**: Automatic formatting fixes on pull requests
- **Benchmarks**: Weekly performance monitoring with regression detection
- **Releases**: Automated PyPI publishing for stable and beta releases
- **Package Validation**: Enforces <2MB core, <8MB with all extras

### Automated Checks
- All tests must pass across Python 3.10-3.12
- Pre-commit hooks (black, isort, flake8, ruff, prettier) pass
- Benchmark regression <10% from baseline
- Code coverage maintained via codecov
- Wheel size stays under 8MB limit
- Type checking (mypy) passes (when configured)

## Environment Variables
```bash
# For testing OCR with real models
export PYTEST_DONUT=yes

# For debugging
export DATAFOG_LOG_LEVEL=DEBUG

# For Spark integration tests  
export PYSPARK_PYTHON=python3
```

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure virtual environment is activated
2. **OCR tests failing**: Install tesseract-ocr system package
3. **Spark tests failing**: Check Java installation
4. **Performance regression**: Run benchmarks to identify cause
5. **Type errors**: Run `mypy datafog/ --ignore-missing-imports`
6. **Pre-commit failing on GitHub**: Run `pre-commit install` and `pre-commit run --all-files` locally before committing
7. **Forgot to run pre-commit**: GitHub Actions will auto-fix formatting issues on PRs

### Getting Help
1. **Check existing tests**: Similar functionality likely tested
2. **Review documentation**: README has comprehensive examples
3. **Run benchmarks**: Performance issues show up in benchmarks
4. **Check CI logs**: GitHub Actions show detailed failure info

## Release Process
1. **Feature complete**: All planned features implemented
2. **Tests passing**: All CI checks green
3. **Performance verified**: Benchmarks within acceptable range
4. **Documentation updated**: README, CHANGELOG, docstrings current
5. **Version bumped**: Update `__version__` in `__about__.py` and `setup.py`
6. **Release tagged**: Create release through GitHub Actions workflow

## Best Practices for Claude Agents

### Code Quality
- **Follow existing patterns**: Look at similar implementations first
- **Add tests**: Every new feature needs corresponding tests
- **Update documentation**: Keep README and docstrings current
- **Check performance**: Run benchmarks for any text processing changes

### Collaboration
- **Small focused PRs**: One feature/fix per branch
- **Clear commit messages**: Use conventional commit format
- **Test thoroughly**: Run full test suite before pushing
- **Review existing code**: Understand patterns before implementing

### Error Handling
- **Graceful degradation**: Handle missing dependencies elegantly  
- **Informative errors**: Provide actionable error messages
- **Logging**: Use logging module for debugging information
- **Type safety**: Use type hints and validate with mypy

