================
Release Roadmap
================

This roadmap outlines the evolution of DataFog from a monolithic package
to a lightweight, modular architecture with optional extras.

.. contents:: Table of Contents
   :local:
   :depth: 1

v4.4.0 - Python 3.13 and v5 Migration Bridge
--------------------------------------------

Before v5.0.0, DataFog should ship a focused v4.4.0 bridge release. The
purpose is to give users a concrete compatibility win while introducing the
v5 direction gently.

v4.4.0 should focus on:

* Python 3.13 support for the core SDK and CLI.
* Dependency validation for optional profiles without blocking core/CLI.
* v5-style preview APIs where they can land safely.
* Targeted deprecation warnings with no warnings on import.
* Migration docs and release notes that announce the v5 path.

Scope artifact:

* :doc:`v44-bridge-release`

v5.0.0 - Offline PII Firewall for AI Apps
-----------------------------------------

The v5.0.0 release is scoped around a sharper adoption wedge:

   DataFog should be the fastest, easiest offline PII firewall for AI apps,
   logs, and datasets.

The release should prioritize trust and time-to-first-value over broad
enterprise surface area. The first path should be a core install, a simple
top-level API, no network surprises, and copy-pasteable workflows for LLM
prompts/outputs, logs, JSONL datasets, and CI checks.

Scope artifacts:

* :doc:`v5-product-brief`
* :doc:`v5-compatibility-matrix`
* :doc:`v5-cut-line`

v5.0.0 must focus on:

* Stable top-level APIs: ``scan``, ``redact``, ``protect``, and ``restore``.
* Privacy-safe defaults: no default network behavior, no runtime package
  installation, and no implicit model downloads.
* Policy-based redaction with presets for LLMs, logs, strict workflows, and
  datasets.
* Reversible token sessions that are explicit and opt-in.
* LLM guardrails, including sync, async, and streaming protection.
* CLI workflows for stdin, files, directories, CSV, JSONL, machine-readable
  output, and CI-friendly exit codes.
* Custom recognizers and stronger structured detection for app/log/secrets
  data.
* Modern packaging and release gates for install profiles, no-network
  behavior, import time, wheel size, accuracy, coverage, and benchmarks.

Deferred to v5.1+:

* OCR overhaul.
* Spark overhaul.
* Cloud DLP integrations.
* Enterprise dashboards and analytics.
* Broad multilingual model tuning.
* Large Presidio-style framework expansion.

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
Version ``4.5.0`` is a focus release for lightweight text PII screening. It
should make the core package easier to install, reason about, test, and use
before larger v5 middleware work.

4.5.0 should focus on:

* Core text scanning, redaction, and guardrail helpers that stay dependency
  light by default.
* Clear install-profile documentation for core, NLP, OCR, Spark, CLI, and web
  surfaces.
* OCR and Spark as supported optional surfaces, not the main 4.5 adoption path.
* Documentation cleanup so users and contributors can find the current package
  story without reading historical planning material first.
* German PII regex support if the external PR passes review and does not
  compromise core precision.

Deferred beyond 4.5.0:

* Full middleware adapters for Sentry, OpenTelemetry, logging frameworks, or
  cloud DLP services.
* OCR architecture overhaul.
* Spark architecture overhaul.
* Enterprise dashboards and analytics.

The lightweight core remains the first path; optional surfaces should stay
explicit and isolated from default import, scan, redact, and guardrail usage.
