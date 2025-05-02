

## ✅ **Story 1.3 – Integrate Regex Annotator into `TextService`**

> **Goal:** Allow `TextService` to support a pluggable engine via `engine="regex" | "spacy" | "auto"`.  
> Regex is fast but simple; spaCy is heavier but deeper. “Auto” tries regex first and falls back only if nothing is found.

---

### 📂 0. **Preconditions**
- [ ] Confirm `RegexAnnotator` is implemented and returns both:
  - `Dict[str, List[str]]` for legacy compatibility
  - `AnnotationResult` for structured output
- [ ] `TextService` should already handle spaCy logic cleanly (Story 1.0)

---

### 🔨 1. Add `engine` Parameter to `TextService`

#### Code:
```python
class TextService:
    def __init__(self, engine: str = "auto", ...):
        assert engine in {"regex", "spacy", "auto"}, "Invalid engine"
        self.engine = engine
        ...
```

---

### ⚙️ 2. Refactor Annotation Logic

Add branching logic to support all three modes.

#### Pseudocode:
```python
def annotate(self, text: str, structured: bool = False):
    if self.engine == "regex":
        result_dict, result_structured = RegexAnnotator().annotate(text)
    elif self.engine == "spacy":
        result_dict, result_structured = SpacyAnnotator().annotate(text)
    elif self.engine == "auto":
        result_dict, result_structured = RegexAnnotator().annotate(text)
        if not any(result_dict.values()):
            result_dict, result_structured = SpacyAnnotator().annotate(text)
    return result_structured if structured else result_dict
```

---

### 🧪 3. Write Integration Tests

#### 3.1 Happy Path (Regex Only)
- [ ] `test_engine_regex_detects_simple_entities()`  
  Inputs: email, phone  
  Asserts: `TextService(engine="regex").annotate(text)` returns expected dict

#### 3.2 Fallback (Auto → SpaCy)
- [ ] `test_engine_auto_fallbacks_to_spacy()`  
  Inputs: Named entities or tricky patterns regex misses  
  Asserts: spaCy is invoked if regex finds nothing

#### 3.3 Explicit SpaCy
- [ ] `test_engine_spacy_only()`  
  Asserts: spaCy is always used regardless of regex hits

#### 3.4 Structured Return
- [ ] `test_structured_annotation_output()`  
  Asserts: `structured=True` returns list of `Span` objects with label/start/end/text

---

### 📏 4. Performance Budget (Optional But Valuable)

- [ ] Add benchmarking test to compare `regex` vs `spacy` on a 10 KB text  
- [ ] Log and confirm regex is ≥5× faster than spaCy in most scenarios

---

### 🧹 5. Clean Up + Docs

- [ ] Update README / docstrings on `TextService`
- [ ] Clearly document `engine` modes and default behavior
- [ ] Add a comment near the `auto` logic explaining fallback threshold

---

