=================
v5.0 Release Line
=================

Status
------

Scope lock draft for what belongs in v5.0.0 versus v5.1+.

v5.0 Release Promise
--------------------

v5.0.0 should ship a sharp, adoption-focused SDK:

   The fastest, easiest offline PII firewall for AI apps, logs, and
   datasets.

The release is not judged by how much surface area it adds. It is judged by
whether a new user can trust it quickly, understand it quickly, and protect
real application data quickly.

Must Ship in v5.0
-----------------

Core API
~~~~~~~~

* Stable top-level ``scan``, ``redact``, ``protect``, and ``restore`` APIs.
* Public typed result objects and entity models.
* Compatibility shims for important v4 APIs.
* API snapshot tests and executable quickstart smoke tests.

Trust Defaults
~~~~~~~~~~~~~~

* Telemetry opt-in or no-network-by-default.
* No runtime package installation.
* No implicit model downloads.
* Safe redaction metadata by default.
* No-network import and core API tests.

Policy and Redaction
~~~~~~~~~~~~~~~~~~~~

* ``RedactionPolicy`` with entity filters, thresholds, locale, mapping
  behavior, and actions per entity type.
* Built-in presets for ``llm``, ``logs``, ``strict``, and ``dataset``.
* Reversible ``TokenSession`` only when explicitly requested.
* HMAC hashing and format-preserving masking strategies.

LLM and App Workflows
~~~~~~~~~~~~~~~~~~~~~

* ``protect`` decorator for sync and async functions.
* Streaming output filtering.
* Guardrail session counters and safe audit metadata.
* Examples for LLM calls, FastAPI middleware, logging filters, LangChain-style
  adapters, and LlamaIndex-style adapters.

CLI and Dataset Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~

* v5 CLI commands: ``scan``, ``redact``, and ``audit``.
* Support for direct text, stdin, files, directories, CSV, and JSONL.
* Machine-readable ``--json`` and ``--jsonl`` output.
* CI-friendly ``--fail-on-detect`` behavior and exit codes.
* Dataset audit summaries that avoid raw PII by default.

Detection Quality
~~~~~~~~~~~~~~~~~

* Custom recognizer registry with regex and validator hooks.
* Common app/log recognizers for secrets, tokens, API keys, IPv6, IBAN,
  crypto wallets, and account identifiers.
* ``us`` and ``global`` locale packs.
* Deterministic overlap resolution and confidence scoring.
* Expanded corpus and enforced accuracy thresholds in CI.

Packaging and Release
~~~~~~~~~~~~~~~~~~~~~

* ``pyproject.toml`` as primary packaging metadata.
* ``py.typed`` marker.
* Clean runtime dependencies and optional extras.
* CI gates for install profiles, import time, wheel size, no-network behavior,
  coverage, accuracy, and benchmark regressions.
* v4 to v5 migration guide and launch assets.

Defer to v5.1+
--------------

OCR Overhaul
~~~~~~~~~~~~

OCR is useful, but it is not the adoption wedge for v5.0. Keep current OCR
compatibility where practical and move OCR quality, preprocessing, and
processor architecture to v5.1+.

Spark and Distributed Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Spark support should not block the first v5 release. Keep install errors and
compatibility sane, then revisit distributed workflows after the core API and
CLI are stable.

Cloud Integrations
~~~~~~~~~~~~~~~~~~

AWS, GCP, Azure, hosted APIs, and cloud DLP bridges are deferred. v5.0 should
win first as an offline local SDK.

Enterprise Analytics
~~~~~~~~~~~~~~~~~~~~

Dashboards, organization-wide reporting, and advanced analytics are deferred.
The v5.0 audit surface should remain CLI/API friendly and privacy-safe.

Broad Multilingual Expansion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

v5.0 may introduce locale structure, but broad multilingual tuning should wait
until the v5 core is stable and measured.

Large Presidio-Style Framework Expansion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DataFog should not try to clone Presidio in v5.0. Custom recognizers are in
scope, but a large enterprise recognizer framework is not.

Scope Creep Test
----------------

A proposed v5.0 item should pass at least one of these tests:

* Does it make first use faster or clearer?
* Does it improve trust for a PII SDK?
* Does it protect LLM, log, CLI, or dataset workflows?
* Does it make the core install smaller, safer, or more predictable?
* Does it reduce migration risk for existing users?

If the answer is no, the item probably belongs in v5.1+.

