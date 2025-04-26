---

### **v4.1.0 — Baseline stability**

* **MUST** read `__version__` from `datafog/__about__.py` and import it in `setup.py`; delete the duplicate there.  
* **MUST** remove every `ensure_installed()` runtime `pip install`; fail fast instead.  
* **MUST** document OCR/Donut extras in `setup.py[extras]`.

---

### **v4.2.0 — Faster spaCy path**

- **MUST** hold the spaCy `nlp` object in a module-level cache (singleton).
- **MUST** replace per-doc loops with `nlp.pipe(batch_size=?, n_process=-1)`.
- **MUST** run spaCy and Tesseract calls in `asyncio.to_thread()` (or a thread-pool) so the event-loop stays free.
- **SHOULD** expose `PIPE_BATCH_SIZE` env var for tuning.

---

### **v4.3.0 — Strong types, predictable output**

- **MUST** make `_process_text` always return `Dict[str, Dict]`.
- **MUST** add `mypy --strict` to CI; fix any revealed issues.
- **SHOULD** convert `datafog.config` to a Pydantic v2 `BaseSettings`.

---

### **v4.4.0 — Clean OCR architecture**

- **MUST** split `ImageService` into `TesseractOCR` and `DonutOCR`, each with `extract_text(Image)->str`.
- **MUST** let users pick via `ImageService(backend="tesseract"|"donut")` or the `DATAFOG_DEFAULT_OCR` env var.
- **SHOULD** add unit tests that stub each backend independently.

---

### **v4.5.0 — Rust-powered pattern matching (optional wheel)**

- **MUST** create a PyO3 extension `datafog._fastregex` that wraps `aho-corasick` / `regex-automata`.
- **MUST** auto-import it when available; fall back to pure-Python silently.
- **SHOULD** publish platform wheels under `pip install "datafog[fastregex]"`.

---

### **v4.6.0 — Streaming and zero-copy**

- **MUST** add `async def stream_text_pipeline(iterable[str]) -> AsyncIterator[Result]`.
- **MUST** scan CSV/JSON via `pyarrow.dataset` to avoid reading the whole file into RAM.
- **SHOULD** provide example notebook comparing latency/bandwidth vs. v4.5.

---

### **v4.7.0 — GPU / transformer toggle**

- **MUST** accept `DataFog(use_gpu=True)` which loads `en_core_web_trf` in half precision if CUDA is present.
- **MUST** fall back gracefully on CPU-only hosts.
- **SHOULD** benchmark and log model choice at INFO level.

---

### **v4.8.0 — Fast anonymizer core**

- **MUST** rewrite `Anonymizer.replace_pii/redact_pii/hash_pii` in Cython (single-pass over the string).
- **MUST** switch hashing to OpenSSL EVP via `cffi` for SHA-256/SHA3-256.
- **SHOULD** guard with `pip install "datafog[fast]"`.

---

### **v4.9.0 — Edge & CI polish**

- **MUST** compile the annotator and anonymizer to WebAssembly using `maturin`, package as `_datafog_wasm`.
- **MUST** auto-load WASM build on `wasmtime` when `import datafog.wasm` succeeds.
- **MUST** cache spaCy model artefacts in GitHub Actions with `actions/cache`, keyed by `model-hash`.
- **SHOULD** update docs and `README.md` badges for new extras and WASM support.

---

Use this ladder as-is, bumping **only the minor version** each time, so v4.0.x callers never break.
