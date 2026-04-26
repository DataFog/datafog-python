=================================
v4.4 Bridge Release Scope
=================================

Status
------

Scope and implementation notes for the v4.4.0 transition release.

Linear project: `DataFog Python v4.4.0: Python 3.13 + v5 Migration Bridge <https://linear.app/threadfork/project/datafog-python-v440-python-313-v5-migration-bridge-0afcd4211a58>`_

Release Thesis
--------------

v4.4.0 should be a bridge release before v5. It should give users an
immediate compatibility win with Python 3.13 and introduce the v5 migration
path without forcing a disruptive API change.

The release should feel positive:

* Python 3.13 support for the core SDK and CLI.
* A preview of the v5-style API path.
* Targeted, actionable deprecation warnings.
* Migration docs that explain what is changing and why.

Required Scope
--------------

Python 3.13 Core and CLI Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

v4.4.0 should support Python 3.13 for the lightweight core package and CLI
workflow.

Required changes:

* Package metadata allows Python 3.13.
* Package classifiers include Python 3.13.
* CI runs the core/CLI profile on Python 3.13.
* Release notes clearly state that Python 3.13 support is guaranteed for
  core and CLI.

Optional Dependency Stance
~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional heavy profiles should be validated where practical, but they should
not block v4.4.0 unless they break the core or CLI install.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Profile
     - v4.4.0 support stance
     - Notes
   * - ``core``
     - Required on Python 3.13
     - Must install and run scan/redaction tests.
   * - ``cli``
     - Required on Python 3.13
     - Must install and run CLI smoke tests.
   * - ``nlp``
     - Validate where practical
     - spaCy advertises Python 3.13 support in current releases, but model
       install behavior should be tested before claiming full support.
   * - ``nlp-advanced``
     - Provisional
     - GLiNER and PyTorch dependency behavior should be tested separately.
   * - ``ocr``
     - Provisional
     - OCR is not on the v4.4 or v5.0 critical path.
   * - ``distributed``
     - Provisional
     - Spark support should not block the bridge release.

v5 Preview APIs
~~~~~~~~~~~~~~~

v4.4.0 should make the recommended v5 path available early where it can be
done without large internal churn.

Preview path:

* ``datafog.scan``
* ``datafog.redact``
* ``datafog.protect`` if it can be exposed through existing guardrail helpers
  without pulling in the full v5 policy engine.

The preview APIs should delegate through current stable internals and should
not require optional heavy dependencies.

For the bridge release, preview APIs should default to the lightweight regex
engine so a core-only install does not emit optional dependency fallback
warnings. Users can still opt into ``engine="smart"`` explicitly.

Deprecation Warning Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~

v4.4.0 should introduce migration signals, not warning noise.

Rules:

* No warnings on ``import datafog``.
* Warnings only fire when selected legacy convenience APIs are called.
* Warning messages name the v5-style replacement.
* Warnings use ``stacklevel`` so they point to user code where practical.
* ``DataFog`` and ``TextService`` should not warn by default in v4.4.0.

Candidate warning targets:

* ``datafog.detect`` -> ``datafog.scan``
* ``datafog.process`` -> ``datafog.redact``

Deferred warning targets:

* ``detect_pii`` -> ``scan``
* ``anonymize_text`` -> ``redact``
* ``scan_text`` -> ``scan``
* Old CLI commands once v5-style CLI aliases exist.

Non-Goals
---------

v4.4.0 should not attempt to complete v5.

Out of scope:

* Full v5 policy engine.
* Reversible token sessions.
* Streaming guardrails.
* OCR overhaul.
* Spark overhaul.
* Modern packaging migration to ``pyproject.toml``.
* Broad dependency cleanup beyond what Python 3.13 requires.

Success Criteria
----------------

v4.4.0 is ready when:

* Python 3.13 core/CLI CI is green.
* Package metadata advertises Python 3.13 support.
* v5-style API docs are visible.
* Deprecation warnings are targeted and tested.
* Release notes frame the release as a compatibility win and migration runway.
