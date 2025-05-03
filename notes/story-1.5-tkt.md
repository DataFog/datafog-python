## ✅ **Story 1.5 – Cleanup and Final Touches**

> **Goal:** Complete final cleanup tasks, ensure type hints are complete, add wheel-size gate to CI, and improve documentation.

---

### 📂 0. **Preconditions**
- [ ] Story 1.4 (Performance Guardrail) is complete and merged
- [ ] All existing tests pass
- [ ] CI pipeline is configured and working

---

### 🧹 1. **Code Cleanup**

#### Tasks:
- [ ] Fix all mypy errors to ensure type hints are complete
- [ ] Address any Pydantic deprecation warnings
- [ ] Ensure all code follows project style guidelines
- [ ] Remove any unused imports or dead code

#### Example mypy command:
```bash
mypy datafog/ --ignore-missing-imports
```

---

### 🔍 2. **Add Wheel-Size Gate to CI**

#### Tasks:
- [ ] Create a script to check wheel size
- [ ] Add CI step to build wheel and verify size is < 8 MB
- [ ] Configure CI to fail if wheel size exceeds limit

#### Example CI Configuration:
```yaml
- name: Build wheel
  run: python -m build --wheel
  
- name: Check wheel size
  run: |
    WHEEL_PATH=$(find dist -name "*.whl")
    WHEEL_SIZE=$(du -m "$WHEEL_PATH" | cut -f1)
    if [ "$WHEEL_SIZE" -ge 8 ]; then
      echo "Wheel size exceeds 8 MB limit: $WHEEL_SIZE MB"
      exit 1
    else
      echo "Wheel size is within limit: $WHEEL_SIZE MB"
    fi
```

---

### 📝 3. **Documentation Improvements**

#### Tasks:
- [ ] Add "When do I need spaCy?" guidance to README
- [ ] Update documentation to reflect all recent changes
- [ ] Create CHANGELOG.md for version 4.1.0
- [ ] Review and update any outdated documentation

#### Example "When do I need spaCy?" Guidance:
```markdown
### When do I need spaCy?

While the regex engine is significantly faster, there are specific scenarios where you might want to use spaCy:

1. **Complex entity recognition**: When you need to identify entities not covered by regex patterns, such as organization names, locations, or product names.

2. **Context-aware detection**: When the meaning of text depends on surrounding context that regex cannot easily capture.

3. **Multi-language support**: When processing text in languages other than English where regex patterns might be insufficient.

4. **Research and exploration**: When experimenting with NLP capabilities and need the full power of a dedicated NLP library.

For high-performance production systems processing large volumes of text with known entity types, the regex engine is recommended.
```

---

### 📋 **Acceptance Criteria**

1. mypy passes with no errors
2. CI includes wheel-size gate (< 8 MB)
3. README includes "When do I need spaCy?" guidance
4. CHANGELOG.md is created with a summary of 4.1.0 changes
5. All documentation is up-to-date and accurate

---

### 📚 **Resources**

- [mypy documentation](https://mypy.readthedocs.io/)
- [GitHub Actions CI configuration](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)
- [Keep a Changelog format](https://keepachangelog.com/)
