=======================
v5 Compatibility Matrix
=======================

Status
------

Scope lock draft for the v4 to v5 migration contract.

Migration Stance
----------------

v5 should be adoption-first without being hostile to existing users.
The default posture is:

* Make the new API obvious and stable.
* Keep existing public APIs working through compatibility shims where
  practical.
* Warn only when a user is on a path that should move to the v5 API.
* Break behavior only when required for trust, privacy, or install
  predictability.

Compatibility Matrix
--------------------

.. list-table::
   :header-rows: 1
   :widths: 26 24 20 30

   * - Surface
     - v4 State
     - v5 Status
     - v5 Direction
   * - ``datafog.scan``
     - v4.4 bridge preview top-level API.
     - Stable public API.
     - Keep as the obvious scan entrypoint returning typed scan results.
   * - ``datafog.redact``
     - v4.4 bridge preview top-level API.
     - Stable public API.
     - Expand user-facing presets and policy support while preserving typed
       redaction metadata.
   * - ``datafog.protect``
     - v4.4 bridge preview alias around ``create_guardrail``.
     - Stable public API.
     - Add decorator/context API for sync, async, and streaming workflows.
   * - ``datafog.restore``
     - No primary public API.
     - Stable public API.
     - Restore text from explicit reversible token sessions only.
   * - ``datafog.sanitize``
     - Top-level LLM helper.
     - Supported shim.
     - Keep as alias-like convenience around ``redact``.
   * - ``datafog.scan_prompt``
     - Top-level LLM helper.
     - Supported shim.
     - Keep for compatibility; docs should prefer ``scan`` or ``protect``.
   * - ``datafog.filter_output``
     - Top-level LLM helper.
     - Supported shim.
     - Keep for compatibility; docs should prefer ``redact`` or ``protect``.
   * - ``datafog.create_guardrail``
     - Top-level guardrail factory.
     - Supported shim.
     - Keep, but docs should make ``protect`` the first path.
   * - ``datafog.detect``
     - Top-level convenience detection API.
     - Deprecated shim.
     - Delegate to ``scan`` and warn with replacement guidance.
   * - ``datafog.process``
     - Top-level detect/process helper.
     - Deprecated shim.
     - Delegate to ``scan`` / ``redact`` and warn with replacement guidance.
   * - ``detect_pii``
     - Core helper returning dicts.
     - Deprecated shim.
     - Keep temporarily for v4 users; prefer ``scan`` typed results.
   * - ``anonymize_text``
     - Core anonymization helper.
     - Deprecated shim.
     - Keep temporarily; prefer ``redact`` with a policy or preset.
   * - ``scan_text``
     - Boolean or dict helper.
     - Deprecated shim.
     - Keep temporarily; prefer ``scan``.
   * - ``get_supported_entities``
     - Returns core regex entity names.
     - Supported utility.
     - Keep, but align with recognizer registry and locale packs.
   * - ``DataFog``
     - Legacy class-based entrypoint.
     - Compatibility shim.
     - Keep through v5 with warnings for new construction patterns.
   * - ``TextService``
     - Service class with engine selection and legacy return shapes.
     - Compatibility shim.
     - Keep for existing users; new docs should use top-level API.
   * - ``TextPIIAnnotator``
     - Lightweight wrapper.
     - Deprecated shim.
     - Keep only if needed for compatibility; prefer ``scan``.
   * - ``RegexAnnotator``
     - Exposed implementation detail.
     - Advanced API.
     - Keep available for advanced users, but docs should prefer registry.
   * - ``datafog.engine``
     - Internal boundary introduced before v5.
     - Internal implementation.
     - Keep stable enough for wrappers, but public imports should use top-level
       APIs or public model paths.
   * - CLI ``scan-text``, ``redact-text``, ``replace-text``, ``hash-text``
     - Current command set.
     - Deprecated command shims.
     - Add v5 ``scan``, ``redact``, and ``audit`` commands; keep old commands
       with warnings.
   * - CLI ``scan-image``
     - OCR-oriented command.
     - Optional legacy command.
     - Keep under OCR extra; do not make it a v5.0 adoption path.
   * - OCR services and processors
     - Optional extras with heavyweight dependencies.
     - Deferred for v5.1+ overhaul.
     - Keep install hints clear; no runtime package installs.
   * - Spark services and UDFs
     - Optional distributed path.
     - Deferred for v5.1+ overhaul.
     - Keep compatibility where practical; no runtime package installs.
   * - Telemetry
     - Opt-in telemetry.
     - Trust-critical behavior change.
     - Keep no-network-by-default.
   * - ``*_lean`` and ``*_original`` modules
     - Parallel historical implementations.
     - Remove or make private after migration path.
     - Consolidate around the v5 core and delete duplicate runtime surfaces.
       In 4.5 these files are marked as non-live shadow modules; removal is
       deferred until legacy tests are migrated or intentionally dropped.

Warning Policy
--------------

Deprecation warnings should be specific and actionable. They should name the
old API, the v5 replacement, and the planned support window. For example:

.. code-block:: text

   datafog.detect() is deprecated in v5. Use datafog.scan() instead.
   This compatibility shim will be supported through the v5.x line.

Breaking-Change Criteria
------------------------

A v5 breaking change is acceptable only when it materially improves one of:

* Privacy or trust defaults.
* Core install reliability.
* No-network behavior.
* Public API clarity.
* Correctness of redaction metadata.
