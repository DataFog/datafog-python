================
v5 Product Brief
================

Status
------

Scope lock draft for DataFog Python v5.0.0.

Linear project: `DataFog Python v5.0.0: Offline PII Firewall for AI Apps <https://linear.app/threadfork/project/datafog-python-v500-offline-pii-firewall-for-ai-apps-78a1550a22f4>`_

Product Thesis
--------------

DataFog v5 should be the fastest, easiest offline PII firewall for AI
apps, logs, and datasets.

The release should optimize for adoption over breadth. The first user
experience should be a small install, a clear one-liner, and strong
privacy defaults:

.. code-block:: python

   import datafog

   result = datafog.redact("Email john@example.com", preset="llm")
   safe_text = result.redacted_text

In the v4.4 bridge release, ``scan``, ``redact``, and ``protect`` should default
to the lightweight regex engine so the core install remains quiet. Higher-recall
NLP paths can stay explicit through ``engine="smart"`` or optional extras.

Primary Users
-------------

v5 is built first for developers who need to keep PII out of:

* LLM prompts and model outputs.
* Agent tool calls and MCP-style tool results.
* Application logs, traces, analytics events, and support dumps.
* JSONL, CSV, and text datasets used for evals or fine-tuning.
* CI checks that should fail when accidental PII is present.

Adoption Principles
-------------------

* **Time to first value under 60 seconds.** A new user should be able to
  install DataFog and redact text without reading architecture docs.
* **No network surprises.** A core install should not send telemetry,
  download models, install packages, or open network connections by
  default.
* **One obvious API path.** The primary path is ``scan``, ``redact``,
  ``protect``, and ``restore``.
* **Safe metadata by default.** Redaction results should not expose
  original PII mappings unless the user explicitly asks for a reversible
  session.
* **Workflow-first docs.** The first examples should be LLM protection,
  logging filters, FastAPI middleware, CLI JSONL redaction, and custom
  recognizers.
* **Honest positioning.** DataFog should not try to out-Presidio
  Presidio. It should win on lightweight offline protection for AI apps,
  logs, and datasets.

v5.0 Must-Haves
---------------

* Stable top-level APIs: ``datafog.scan``, ``datafog.redact``,
  ``datafog.protect``, and ``datafog.restore``.
* Public typed result objects for scans, entities, redaction results,
  and reversible sessions.
* Privacy-safe defaults: telemetry opt-in or no-network-by-default,
  no runtime package installation, no implicit model downloads.
* Policy-based redaction with presets for ``llm``, ``logs``,
  ``strict``, and ``dataset``.
* Reversible token sessions for workflows that need explicit
  restore support.
* LLM guardrails for sync, async, and streaming responses.
* CLI support for stdin, files, directories, CSV, JSONL, machine-readable
  output, and CI-friendly exit codes.
* Custom recognizer registry for domain-specific PII and secrets.
* Expanded corpus tests for app, log, and secret-like data.
* Modern packaging, typed package marker, install-profile tests, and
  release gates for accuracy, coverage, import time, wheel size, and
  no-network behavior.

Non-Goals for v5.0
------------------

The following work is intentionally outside the v5.0 critical path:

* OCR overhaul.
* Spark overhaul.
* Cloud DLP integrations.
* Enterprise dashboards or analytics products.
* Broad multilingual model tuning.
* A large Presidio-style recognizer framework.
* Hosted service features.

Success Metrics
---------------

* A clean core install can redact text in under 60 seconds from a fresh
  environment.
* ``pip install datafog`` stays lightweight and does not require spaCy,
  PyTorch, OCR, Spark, or model downloads.
* ``import datafog`` and core ``scan`` / ``redact`` calls make no network
  requests by default.
* The README quickstart uses the v5 API first and does not require legacy
  classes.
* At least five adoption workflows are documented and copy-pasteable:
  LLM prompts/outputs, streaming outputs, logging, FastAPI, and JSONL CLI.
* Accuracy and regression checks run in CI and produce readable artifacts.
* Existing v4 users have a clear migration path with compatibility shims
  and warnings instead of surprising breakage.
