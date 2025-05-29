
## 🔬 GLiNER Research Phase Instructions

### Objective
Validate GLiNER's performance characteristics and compatibility with DataFog to inform v4.2.0 integration decisions.

### Setup & Environment
```bash
# 1. Create isolated research environment
python -m venv gliner_research_env
source gliner_research_env/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 2. Install GLiNER and dependencies
pip install gliner torch transformers
pip install pandas  # for data analysis
pip install pytest-benchmark  # for timing tests
```

### Research Tasks (2-3 days)

#### Task 1: Basic GLiNER Functionality Validation
```python
# Test basic GLiNER operation
from gliner import GLiNER

# Load default model
model = GLiNER.from_pretrained('urchade/gliner_base')

# Test with DataFog-style PII text
test_text = "Contact John Doe at john.doe@company.com or call (555) 123-4567. His SSN is 123-45-6789."

# Test GLiNER's natural language labels
labels = ['person', 'email address', 'phone number', 'social security number', 'organization', 'location']

entities = model.predict_entities(test_text, labels, threshold=0.5)
print("GLiNER Results:", entities)
```

#### Task 2: Performance Benchmarking
Compare GLiNER against DataFog's existing performance baselines:

```python
# Benchmark against DataFog's test data
# Use the same 10KB text that showed 190x regex advantage
import time

def benchmark_engine(engine_func, text, iterations=10):
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = engine_func(text)
        end = time.perf_counter()
        times.append(end - start)
    
    avg_time = sum(times) / len(times)
    return avg_time, len(result) if result else 0

# Test with DataFog's standard 10KB business document
# Record: processing time, entities found, memory usage
```

**Key Metrics to Capture:**
- Processing time for 10KB text (compare to regex 2.4ms, spaCy 459ms)
- Model loading time (first run vs subsequent runs)
- Memory usage during processing
- Number and types of entities detected

#### Task 3: Entity Type Mapping Analysis
```python
# Map GLiNER outputs to DataFog's expected format
gliner_entities = model.predict_entities(test_text, labels)

# Document mapping between:
# GLiNER format: [{'start': 8, 'end': 16, 'text': 'John Doe', 'label': 'person'}]
# DataFog format: {'PERSON': ['John Doe'], 'EMAIL': ['john.doe@company.com']}

def map_gliner_to_datafog(gliner_entities):
    # Create mapping function
    mapping = {
        'person': 'PERSON',
        'email address': 'EMAIL', 
        'phone number': 'PHONE',
        'social security number': 'SSN',
        # ... document all mappings
    }
    # Implementation here
```

#### Task 4: Model Comparison
Test different GLiNER models to find the best fit:
- `urchade/gliner_base` (default)
- `urchade/gliner_medium-v2.1` 
- `urchade/gliner_large-v2.1`

Record for each:
- Model size/download time
- Processing speed
- Entity detection accuracy
- Memory usage

#### Task 5: PII Detection Accuracy Test
```python
# Create test cases with known PII entities
test_cases = [
    {
        'text': 'Email john@example.com, phone (555) 123-4567',
        'expected': {'EMAIL': ['john@example.com'], 'PHONE': ['(555) 123-4567']}
    },
    # Add more test cases covering different PII types
]

# Compare GLiNER vs regex vs spaCy accuracy
```

### Deliverables Expected

#### 1. Performance Report
```markdown
# GLiNER Performance Analysis

## Speed Comparison (10KB text)
- Regex: 2.4ms (baseline)
- GLiNER: XXXms (XXx slower than regex, XXx vs spaCy)
- spaCy: 459ms

## Model Loading
- First load: XXX seconds
- Subsequent calls: XXX ms

## Memory Usage
- Model loading: XXX MB
- Processing: XXX MB peak
```

#### 2. Entity Mapping Schema
Document the complete mapping between GLiNER labels and DataFog entity types.

#### 3. Recommendation Report
```markdown
# GLiNER Integration Recommendation

## Performance Position
- GLiNER is [faster/slower] than spaCy by XXx
- Suitable for [real-time/batch] processing
- Memory requirements: [acceptable/concerning] for production

## Recommended Integration Approach
- Model: [gliner_base/medium/large]
- Position in cascade: [before/after] spaCy
- Use cases: [contextual entities/general PII/specific scenarios]

## Risk Assessment
- Performance impact: [low/medium/high]
- Installation complexity: [simple/moderate/complex]
- Maintenance overhead: [low/medium/high]
```

### Success Criteria
- [ ] GLiNER successfully processes DataFog's test data
- [ ] Performance characteristics documented vs existing engines
- [ ] Entity type mapping strategy defined
- [ ] Clear recommendation for integration approach
- [ ] Identified optimal GLiNER model for DataFog use cases

### Timeline
- **Day 1**: Setup, basic functionality, initial benchmarking
- **Day 2**: Comprehensive performance testing, model comparison
- **Day 3**: Entity mapping, accuracy analysis, final recommendations

The goal is to determine if GLiNER adds value to DataFog's engine hierarchy and where it should be positioned relative to the existing 190x regex advantage and comprehensive spaCy coverage.