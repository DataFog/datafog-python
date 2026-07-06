================
Release Roadmap
================

Where DataFog is today (4.7.x) and where it is going (v5.0.0). The 4.x
line delivered the lightweight-core architecture and, from 4.6.0 on, an
offline PII firewall for AI agents and gateways. The v5 cycle turns that
foundation into the fastest, easiest offline PII firewall for AI apps,
logs, and datasets.

.. contents:: Table of Contents
   :local:
   :depth: 1

Current status — 4.7.x
----------------------

DataFog ``4.7.0`` is the current stable release (July 2026). Patch
releases on the 4.7.x line focus on detection precision — reducing
SSN/phone false positives surfaced by real-world agent traffic — while
v5.0.0 is prepared.

Every published performance number is reproducible with one command:
``python benchmarks/run.py`` (see ``benchmarks/`` for methodology,
pinned payloads, and comparisons against Presidio and spaCy NER).

✅ 4.1.0 — Lightweight Core (Released)
--------------------------------------

A major architectural shift to a lightweight core with optional extras:

* **Core package size reduced** from ~8MB to <2MB
* **Dependency splitting** into optional extras (nlp, ocr, distributed, etc.)
* **Simple API** with ``detect()`` and ``process()`` functions
* **Graceful degradation** when optional dependencies are not installed
* **100x+ performance advantage** over NER-based detection, now
  reproducible with one command (``python benchmarks/run.py``)

.. code-block:: bash

   pip install datafog          # lightweight core (regex engine only)
   pip install datafog[nlp]     # with spaCy
   pip install datafog[ocr]     # with OCR
   pip install datafog[all]     # everything

✅ 4.2.x – 4.3.x — Engines and Operations (Released)
----------------------------------------------------

* **GLiNER engine** (4.2.0): modern NER via the ``nlp-advanced`` extra,
  with a ``smart`` cascade mode.
* **Anonymous opt-out telemetry** (4.3.0) and consolidated CI workflows.
* Sample notebooks and performance-regression fixes.

✅ 4.4.0 — Python 3.13 and v5 Migration Bridge (Released)
----------------------------------------------------------

The bridge release that introduced the v5 direction gently:

* Python 3.13 support for the core SDK and CLI.
* Dependency validation for optional profiles without blocking core/CLI.
* v5-style preview APIs where they could land safely.
* Targeted deprecation warnings with no warnings on import.
* Migration docs and release notes announcing the v5 path.

Scope artifacts: :doc:`v44-bridge-release`

✅ 4.5.0 — Lightweight Text PII Screening (Released July 2026)
---------------------------------------------------------------

A focus release that made the core package easier to install, reason
about, test, and use:

* Core text scanning, redaction, and guardrail helpers that stay
  dependency-light by default (``scan``, ``redact``, ``protect`` previews).
* Clear install-profile documentation for core, NLP, OCR, Spark, CLI, and
  web surfaces.
* German PII locale support.
* Documentation cleanup separating the current package story from
  historical planning material.

Scope artifacts: :doc:`v45-release-readiness`

✅ 4.6.0 — Agent & Gateway Firewall (Released July 2026)
---------------------------------------------------------

Two ready-made enforcement points that catch PII at the moment it would
leave the machine — offline, with matched values never echoed into logs
or transcripts:

* **Claude Code hook** (``datafog-hook``): gates agent tool calls
  (shell commands, web requests, file writes, MCP tools) and warns the
  model when prompts or tool results carry PII. ~70–90ms per invocation
  including process startup; also installable as the
  `Claude Code plugin <https://github.com/DataFog/datafog-claude-plugin>`_.
* **LiteLLM guardrail** (``DataFogGuardrail``): redacts or blocks PII in
  requests and responses at the gateway, for any LiteLLM-proxied
  provider. In-process, ~40µs per message scanned — no sidecar service.

Both default to the high-precision entity set (``EMAIL``, ``PHONE``,
``CREDIT_CARD``, ``SSN``); noisier types are opt-in.

✅ 4.7.0 — Allowlists and Typing (Released July 2026)
------------------------------------------------------

* **Allowlist support**: ``allowlist=[...]`` for exact values and
  ``allowlist_patterns=[...]`` for full-match regexes (ReDoS-hardened),
  available in the API and both firewall adapters.
* **Presidio-style entity aliases** (``EMAIL_ADDRESS``, ``PHONE_NUMBER``,
  ``US_SSN``) for easy migration.
* **py.typed** marker for type-checker support.

4.7.x patch releases: SSN and phone precision fixes (hex-string and
no-dash false positives).

v5.0.0 — Offline PII Firewall for AI Apps (In Progress)
--------------------------------------------------------

The v5.0.0 release is scoped around a sharper adoption wedge:

   DataFog should be the fastest, easiest offline PII firewall for AI apps,
   logs, and datasets.

The release prioritizes trust and time-to-first-value over broad
enterprise surface area: a core install, a simple top-level API, no
network surprises, and copy-pasteable workflows for LLM prompts/outputs,
logs, JSONL datasets, and CI checks.

Themes:

* **Precision**: a zero-dependency validation pass on every hit (Luhn,
  IBAN mod-97, SSN structure rules, IP plausibility), confidence scores
  on findings, and strictness presets (``strict`` / ``balanced`` /
  ``lenient``) — with precision/recall benchmarks published alongside the
  speed benchmarks.
* **EU language & entity coverage**: generalize 4.5's German support into
  a locale pack system (new languages become data plus tests, not code
  changes), starting with locale-independent EU entities (IBAN, VAT IDs,
  national ID formats).
* **A leaner package**: core stays pydantic-only; the Donut/transformers
  OCR path is removed (pytesseract remains), the PySpark wrapper becomes
  a documented recipe, legacy duplicate modules are deleted, and CI
  enforces wheel-size and import-time budgets.
* **Built for pipelines**: pure, stateless, thread-safe ``scan``/``redact``
  with batch/iterator APIs, plus recipes for Kafka consumers,
  Vector/Fluent Bit transforms, and OpenTelemetry collector processors.
* **Vault-friendly anonymization**: deterministic tokenization with
  exportable mappings and format-preserving pseudonymization.

API direction: ``scan()``, ``redact()``, ``protect()``, and ``restore()``
become the primary documented API; legacy ``detect()``/``process()`` keep
working as compatibility shims throughout the v5.x line.

Deferred to v5.1+:

* OCR overhaul.
* Spark overhaul.
* Cloud DLP integrations.
* Enterprise dashboards and analytics.
* Broad multilingual model tuning.
* Large Presidio-style framework expansion.

Scope artifacts:

* :doc:`v5-product-brief`
* :doc:`v5-compatibility-matrix`
* :doc:`v5-cut-line`
