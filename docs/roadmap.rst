================
Release Roadmap
================

This roadmap outlines the evolution of DataFog from a monolithic package
to a lightweight, modular architecture with optional extras.

.. contents:: Table of Contents
   :local:
   :depth: 1

✅ 4.1.0 (Released)
--------------------
The ``4.1.0`` release represents a major architectural shift to a lightweight
core with optional extras. **Key achievements:**

**Lightweight Architecture**

* **Core package size reduced** from ~8MB to <2MB
* **Dependency splitting** into optional extras (nlp, ocr, distributed, etc.)
* **Simple API** with ``detect()`` and ``process()`` functions
* **Graceful degradation** when optional dependencies not installed

**Performance Validation**

* **190x performance advantage** over spaCy validated with fair benchmarks
* **Independent benchmark scripts** for transparent performance claims
* **Regex engine optimization** maintaining sub-3ms processing times

**Developer Experience**

* **Streamlined CI/CD** with unified workflows and pre-commit integration
* **Auto-fix PRs** for formatting issues
* **Comprehensive testing** including dependency isolation tests

**Critical Stability Fixes (December 2024)**

* **CI/CD stabilization** with 87% test success rate (156/180 tests passing)
* **Structured output bug resolution** for multi-chunk text processing
* **Conditional testing architecture** preserving lean design while enabling full feature testing
* **Mock fixture corrections** for proper service isolation in tests
* **Benchmark test validation** ensuring performance claims remain verifiable

**Installation Options**

.. code-block:: bash

   # Lightweight core (regex engine only)
   pip install datafog
   
   # With spaCy for advanced NLP
   pip install datafog[nlp]
   
   # With OCR capabilities
   pip install datafog[ocr]
   
   # Full functionality
   pip install datafog[all]

4.2.x – 4.4.x
--------------
Subsequent minor releases will focus on:

* **Enhanced regex patterns** for new entity types
* **Performance optimizations** maintaining 150x+ speedup advantage
* **Additional anonymization methods** (advanced hashing, format-preserving)
* **Improved OCR accuracy** with preprocessing pipelines
* **Extended CLI capabilities** for batch processing

All features will remain backward compatible with the lightweight architecture.

4.5.0
------
Version ``4.5.0`` will introduce:

* **Enterprise features** in dedicated extras
* **Advanced analytics** for PII detection patterns
* **Multi-language support** for international PII types
* **Cloud integration** helpers for AWS, GCP, Azure
* **Performance monitoring** and metrics collection

The lightweight core will remain unchanged, ensuring existing
integrations continue to work without modification.