===============
Live Module Map
===============

This map identifies the live modules for DataFog 4.5 and the historical
shadow files that should not be used for new work. The goal is to make the
current code path obvious without removing importable legacy files that still
have test coverage or historical value.

Live 4.5 Modules
================

.. list-table::
   :header-rows: 1

   * - Concept
     - Live module
     - Notes
   * - Package exports
     - ``datafog/__init__.py``
     - Top-level ``scan``, ``redact``, guardrail helpers, compatibility shims,
       and lazy optional exports.
   * - Core engine
     - ``datafog/engine.py``
     - Dataclass-based scan/redact path used by the 4.5 core helpers.
   * - Agent helpers
     - ``datafog/agent.py``
     - Prompt/output screening and guardrail helpers on the lightweight text
       path.
   * - Backward-compatible ``DataFog`` class
     - ``datafog/main.py``
     - Current public ``DataFog`` class and text/OCR compatibility methods.
   * - Text service
     - ``datafog/services/text_service.py``
     - Current service boundary for regex, spaCy, GLiNER, auto, and smart
       engines.
   * - CLI
     - ``datafog/client.py``
     - Current command-line entrypoint.
   * - OCR surface
     - ``datafog/services/image_service.py`` and
       ``datafog/processing/image_processing/``
     - Optional image/OCR surface behind explicit extras.
   * - Spark surface
     - ``datafog/services/spark_service.py`` and
       ``datafog/processing/spark_processing/``
     - Optional distributed surface behind explicit extras.
   * - Packaging
     - ``setup.py`` and ``requirements-*.txt``
     - Current packaging and contributor dependency inputs.

Historical Shadow Files
=======================

The following files are historical snapshots or alternate implementation
lineage. They are kept importable for now, but new work should not add behavior
to them.

.. list-table::
   :header-rows: 1

   * - Historical file
     - Live replacement
     - 4.5 status
   * - ``datafog/__init___lean.py``
     - ``datafog/__init__.py``
     - Historical package export snapshot.
   * - ``datafog/__init___original.py``
     - ``datafog/__init__.py``
     - Historical eager-export package snapshot.
   * - ``datafog/main_lean.py``
     - ``datafog/main.py``
     - Historical lightweight ``DataFog`` implementation.
   * - ``datafog/main_original.py``
     - ``datafog/main.py`` plus optional OCR/Spark services
     - Historical full-featured ``DataFog`` implementation still referenced by
       legacy tests.
   * - ``datafog/services/text_service_lean.py``
     - ``datafog/services/text_service.py``
     - Historical regex-first service variant.
   * - ``datafog/services/text_service_original.py``
     - ``datafog/services/text_service.py``
     - Historical spaCy/regex service still referenced by legacy tests.
   * - ``setup_lean.py``
     - ``setup.py``
     - Historical packaging snapshot.
   * - ``setup_original.py``
     - ``setup.py``
     - Historical packaging snapshot.

Cleanup Boundary
================

This 4.5 slice marks the shadow files as non-live and documents their live
replacements. It does not remove importable modules because ``main_original``
and ``text_service_original`` still have explicit legacy tests. A future
breaking cleanup can remove the shadow files after any remaining tested
behavior is either migrated to live modules or intentionally dropped with a
compatibility note.
