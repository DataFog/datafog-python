### TDD Plan for Story 1.2: _Design the regex fallback spec_

#### 1. **Setup Testing Environment**

- [ ] Create a new test module (e.g., `test_regex_annotator.py`)
- [ ] Import `pytest` and set up fixtures if needed

#### 2. **Write Failing Tests First**

##### 2.1 Entity Patterns (regex)

For each label below, write a unit test with:

- One clearly matching string
- One edge-case false negative
- One false positive to avoid

- [ ] `test_email_regex()`
- [ ] `test_phone_regex()`
- [ ] `test_ssn_regex()`
- [ ] `test_credit_card_regex()`
- [ ] `test_ip_address_regex()`
- [ ] `test_dob_regex()`
- [ ] `test_zip_regex()`

##### 2.2 Return Schema

- [ ] `test_annotation_dict_format()`  
       Assert that a sample input returns `Dict[str, List[str]]` with correct keys and values.

- [ ] `test_annotation_result_format()`  
       Assert that the structured `AnnotationResult` returns correct spans with offsets and labels.

##### 2.3 Performance Constraint

- [ ] `test_regex_performance()`  
       Benchmark annotation on a 10 KB input and assert runtime < 200 µs.

##### 2.4 Edge Case Policy

- [ ] `test_invalid_ip_filtered()`  
       Ensure IPs like `999.999.999.999` or `256.1.1.1` are skipped.

- [ ] `test_loose_date_acceptance()`  
       Accept both `01/01/2000` and `2000-01-01`.

- [ ] `test_tricky_email_rejection()`  
       Reject `foo@[123.456.789.000]`.

##### 2.5 Contract Compliance

- [ ] `test_output_keys_match_labels()`  
       Ensure output dict keys are exactly: `EMAIL`, `PHONE`, `SSN`, `CREDIT_CARD`, `IP_ADDRESS`, `DOB`, `ZIP`.

---

#### 3. **Stub Out Regex Annotator**

- [ ] Create a skeleton module: `regex_annotator.py`
- [ ] Define pattern table (label → compiled regex)
- [ ] Define `Span` and `AnnotationResult` classes
- [ ] Stub `annotate(text: str)` to return fixed values

---

#### 4. **Iteratively Implement Logic**

- [ ] Implement each regex and rerun tests until each corresponding test passes.
- [ ] Implement span extraction logic using `re.finditer`.
- [ ] Implement both `dict` and `structured` output formats.
- [ ] Optimize for performance — compile all patterns once, run in sequence.

---

#### 5. **Refactor**

- [ ] Group tests using parameterization where possible
- [ ] Add fixtures for shared input text
- [ ] Split long regex into readable multiline strings (with `re.VERBOSE` if needed)

---
