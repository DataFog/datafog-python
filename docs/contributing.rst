=======================================
Contributor Setup And 4.5 Release Flow
=======================================

This page is the contributor runbook for DataFog 4.5 work. It is meant for
humans and agents preparing local changes, choosing verification commands, and
understanding where the 4.5 release boundary sits.

Version Frame
=============

Current release planning uses this frame:

* Stable package release: ``4.4.0``.
* Current development package version: ``4.4.0a5``.
* Next minor target: ``4.5.0``.

Do not bump routine feature, documentation, or cleanup branches directly to
``4.5.0``. Keep the version stable during local release-prep work, then handle
the final version and release-note alignment in the release-readiness slice.

Python Environments
===================

DataFog currently declares support for Python ``>=3.10,<3.14``. The CI matrix
tests core installs on Python 3.10, 3.11, 3.12, and 3.13. Optional NLP and
NLP-advanced profiles are tested on Python 3.10, 3.11, and 3.12; Python 3.13
optional-profile validation is tracked separately for 4.5.

Create one virtual environment per Python version when you need to compare
profiles locally:

.. code-block:: bash

   python3.12 -m venv .venv312
   source .venv312/bin/activate
   python -m pip install --upgrade pip

For another version, keep the environment name explicit:

.. code-block:: bash

   python3.10 -m venv .venv310
   python3.11 -m venv .venv311
   python3.13 -m venv .venv313

Install Profiles
================

Install the package in editable mode with the smallest profile that matches the
work you are doing:

.. list-table::
   :header-rows: 1

   * - Profile
     - Command
     - Notes
   * - Core
     - ``pip install -e .``
     - Lightweight regex engine and package import path.
   * - Core test + CLI
     - ``pip install -e ".[test,cli]" -r requirements-test.txt``
     - Matches the core CI test profile.
   * - Docs
     - ``pip install -e ".[docs]" -r requirements-docs.txt``
     - Enough to build Sphinx docs locally.
   * - Local dev
     - ``pip install -e ".[dev,cli]" && pip install -r requirements-dev.txt``
     - Test, docs, lint, formatting, and pre-commit tooling.
   * - NLP
     - ``pip install -e ".[test,cli,nlp]" -r requirements-test.txt``
     - Also install the spaCy model needed for NLP tests.
   * - NLP advanced
     - ``pip install -e ".[test,cli,nlp,nlp-advanced]" -r requirements-test.txt``
     - Also install spaCy and GLiNER models explicitly.
   * - OCR
     - ``pip install -e ".[test,ocr]" -r requirements-test.txt``
     - Tesseract workflows also need the system ``tesseract`` binary.
   * - Distributed
     - ``pip install -e ".[test,distributed]" -r requirements-test.txt``
     - Spark workflows also need a Java runtime.
   * - All extras
     - ``pip install -e ".[all,dev]"``
     - Use only when you deliberately want every optional surface locally.

Optional model setup is explicit:

.. code-block:: bash

   python -m spacy download en_core_web_lg
   datafog download-model urchade/gliner_multi_pii-v1 --engine gliner

Focused Verification
====================

Use focused checks for the area you touched before running broader suites.
Set the no-telemetry environment variables when testing core privacy and import
behavior:

.. code-block:: bash

   export DATAFOG_NO_TELEMETRY=1
   export DO_NOT_TRACK=1

Core dependency and no-network checks:

.. code-block:: bash

   python -m pytest tests/test_runtime_dependency_safety.py tests/test_no_network_core.py -q

Run a changed test file directly when behavior changes:

.. code-block:: bash

   python -m pytest tests/test_engine_api.py -q
   python -m pytest tests/test_agent_api.py -q
   python -m pytest tests/test_cli_smoke.py -q

Docs build:

.. code-block:: bash

   python -m sphinx -b html docs docs/_build/html

Pre-commit on touched files:

.. code-block:: bash

   pre-commit run --files README.md docs/index.rst --show-diff-on-failure
   git diff --check

Broad Verification
==================

Run the broad non-slow suite when a change affects shared behavior,
public docs, imports, packaging, or release confidence:

.. code-block:: bash

   python -m pytest -m "not slow" -q

To mimic the core CI profile more closely:

.. code-block:: bash

   python -m pytest tests/ \
     -m "not slow" \
     --ignore=tests/test_gliner_annotator.py \
     --ignore=tests/test_image_service.py \
     --ignore=tests/test_ocr_integration.py \
     --ignore=tests/test_spark_integration.py \
     --ignore=tests/test_text_service_integration.py

Use optional-profile smoke checks when changing extras, dependency boundaries,
or install behavior:

.. code-block:: bash

   DATAFOG_INSTALL_PROFILE=core python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=cli python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=nlp python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=nlp-advanced python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=ocr python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=distributed python -m pytest tests/test_install_profiles.py -q
   DATAFOG_INSTALL_PROFILE=web python -m pytest tests/test_install_profiles.py -q

4.5 Release Flow
================

The 4.5 work lands as focused pull requests into ``dev``. Keep feature and docs
branches narrow, and avoid mixing local cleanup, external PR review, and final
release mechanics in one branch.

The release flow for 4.5 is:

1. Land the local release-prep baseline and follow-up cleanup/docs slices.
2. Review the external German regex PR after the local release-prep baseline is
   in place.
3. Integrate German regex support only if review says it fits the 4.5
   lightweight text screening thesis.
4. Validate optional Python 3.13 profiles before claiming support beyond core
   SDK and CLI.
5. Prepare release readiness: changelog/release notes, package checks, docs
   build, CI state, and version alignment.
6. Bump or override the final stable release to ``4.5.0`` only during the
   release-readiness and stable-release path.

The current release workflow strips prerelease suffixes from the package
version unless a manual stable ``version_override`` is provided. For the final
4.5 stable release, use a dedicated release-readiness change or the stable
workflow override so the published version is ``4.5.0`` rather than another
``4.4.0`` prerelease line.

External PR Boundary
====================

The external German PII regex PR belongs after local baseline cleanup. Review
it as a 4.5 candidate, not as a v5 planning shortcut. If accepted, adapt it in
the German regex integration slice with tests, documentation of locale
coverage, and no new dependency burden on the core path.
