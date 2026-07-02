======================
v4.5 Release Readiness
======================

This page is the release-readiness artifact for DataFog 4.5.0. It summarizes
the intended release story, the final version alignment path, and the checks
that should be true before promoting the release.

Release Position
================

DataFog 4.5.0 is a lightweight text PII screening focus release. It should make
the current package easier to install, read, test, and contribute to while
building toward a sharper v5 middleware direction.

The 4.5 release includes:

* Core text scanning, redaction, and guardrail helpers that stay dependency
  light by default.
* Regex-only German structured PII support with broad German identifiers gated
  behind explicit locale or entity selection.
* Clear optional-profile documentation for NLP, OCR, Spark, CLI, web, and
  install-profile testing.
* Python 3.13 validation for the core SDK, CLI, ``nlp``, ``nlp-advanced``, and
  ``ocr`` profiles.
* Telemetry documentation that states the existing opt-in behavior and opt-out
  controls without changing runtime defaults.

The 4.5 release does not include:

* A v5 package break.
* Dedicated Sentry, OpenTelemetry, logging-framework, or cloud DLP middleware
  adapters.
* An OCR or Spark architecture overhaul.
* Full certification of ``distributed`` or ``all`` install profiles on
  Python 3.13.

Release Notes Draft
===================

Use this framing for the GitHub release notes and package announcement:

   DataFog 4.5.0 is a focused release for lightweight text PII screening. The
   core install remains dependency-light while the text APIs, CLI, guardrail
   helpers, German structured PII coverage, optional-profile docs, and Python
   3.13 compatibility story become clearer and easier to verify.

Call out these user-facing points:

* German structured identifiers — VAT IDs, IBANs, tax IDs, postal codes,
  passport numbers, residence permit numbers, and pension insurance numbers —
  are locale-gated and require ``locales=["de"]`` or explicit entity
  selection. Default (no-locale) detection behavior is unchanged from 4.4.0.
* Guardrail helpers (``sanitize``, ``scan_prompt``, ``filter_output``,
  ``create_guardrail``) now default to the regex engine; pass
  ``engine="smart"`` to restore 4.4.0's NER-backed helper behavior.
* OCR and Spark remain supported optional surfaces. They are not deprecated,
  but their broader overhaul is deferred beyond 4.5.
* Telemetry remains disabled unless ``DATAFOG_TELEMETRY=1`` is set.
  ``DATAFOG_NO_TELEMETRY=1`` and ``DO_NOT_TRACK=1`` continue to force it off.
* Python 3.13 is certified for core SDK, CLI, ``nlp``, ``nlp-advanced``, and
  ``ocr``. Donut OCR still requires a model already available locally.

Version Alignment
=================

The source of truth for the package version is ``datafog/__about__.py``.
``setup.py`` reads that value during packaging, and ``docs/conf.py`` reads the
same value for the Sphinx ``release`` field.

Before stable release promotion:

* Stable package release: ``4.4.0``.
* Current development package version: ``4.4.0a5``.
* Next stable target: ``4.5.0``.

Do not bump routine feature or documentation branches directly to ``4.5.0``.
For the stable release, promote the merged 4.5 stack and either:

* trigger the release workflow with ``release_type=stable`` and
  ``version_override=4.5.0``, or
* make a dedicated stable-release bump that updates ``datafog/__about__.py``
  and reruns the docs build so Sphinx reports ``v4.5.0``.

After the bump path is chosen, verify:

* ``python -c "import datafog; print(datafog.__version__)"`` prints
  ``4.5.0`` from the release build environment.
* Built package metadata reports ``Version: 4.5.0``.
* Built docs report ``v4.5.0`` through ``docs/conf.py``.
* ``CHANGELOG.MD`` and the GitHub release notes both describe the 4.5 focus
  release rather than v5 planning work.

Readiness Checklist
===================

Run these gates before promoting 4.5.0:

.. list-table::
   :header-rows: 1

   * - Gate
     - Command or evidence
   * - Formatting and static checks
     - ``pre-commit run --all-files --show-diff-on-failure`` and
       ``git diff --check``
   * - Docs build
     - ``python -m sphinx -b html docs docs/_build/html``
   * - Core no-network and dependency boundary
     - ``DATAFOG_NO_TELEMETRY=1 DO_NOT_TRACK=1 python -m pytest tests/test_runtime_dependency_safety.py tests/test_no_network_core.py -q``
   * - German regex behavior
     - ``python -m pytest tests/test_de_pii_regex.py tests/test_regex_annotator.py -q``
   * - Broad non-slow suite
     - ``DATAFOG_NO_TELEMETRY=1 DO_NOT_TRACK=1 python -m pytest -m "not slow" -q``
   * - Install-profile smoke checks
     - ``DATAFOG_INSTALL_PROFILE=<profile> python -m pytest tests/test_install_profiles.py -q`` for ``core``, ``cli``, ``nlp``, ``nlp-advanced``, ``ocr``, ``distributed``, and ``web``
   * - OCR system smoke
     - ``DATAFOG_INSTALL_PROFILE=ocr DATAFOG_REQUIRE_TESSERACT=1 python -m pytest tests/test_install_profiles.py -q``
   * - Package build
     - ``python -m build`` and ``python scripts/check_wheel_size.py``
   * - GitHub CI
     - The final release-readiness PR and the merged release branch have green
       CI, including Python 3.13 profile coverage.
   * - Stable release dry run
     - Trigger ``release_type=stable``, ``version_override=4.5.0``,
       ``dry_run=true`` before publishing.

Review Notes
============

German regex support is included in 4.5 with documented default and opt-in
behavior. The external PR was treated as review input rather than merged
unchanged, because broad German identifiers need locale or contextual gating to
avoid noisy default detection.

OCR and Spark remain documented as optional surfaces. They should not be
described as deprecated, and they should not be positioned as the primary 4.5
adoption path.

The v5 planning pages remain useful context, but the 4.5 release should not
claim middleware adapters, a package break, or a complete optional-surface
redesign.
