=====================
DataFog Documentation
=====================

DataFog is a lightweight text PII screening package for Python. The
primary path is a small core install, fast regex-based scanning and redaction,
agent-friendly guardrail helpers, and explicit optional extras when you need
NLP, OCR, Spark, or web inputs.

Start with :doc:`getting-started` if you want the shortest route from install
to scanning text. The roadmap and historical planning pages remain available,
but the live user docs are the first path for current text APIs.

4.9.0 migration bridge
======================

DataFog 4.9.0 is the migration bridge to the planned Rust-backed 5.0 API.
Upgrade the base package with ``python -m pip install --upgrade datafog==4.9.0``;
the native dependency remains optional. The ``rust`` extra requires
``datafog-core>=0.4.0,<0.5`` and capability contract version 1.

4.9 preserves existing imports, result classes, Python detection defaults, and
redaction behavior. It adds explicit experimental Rust detection through
``backend="rust"``, the ``datafog.compat.v4`` facade, and the ``datafog.v5`` native
Core schema preview. See :doc:`python-sdk` and the
:download:`complete 4.9 migration guide <migration-4.9.md>`.

DataFog 4.9.0 deprecates ``detect()``/``process()``, OCR, and Spark for
removal in 5.0. The earlier promise to retain ``detect()``/``process()`` throughout
5.x is revised. OCR/Spark remain functional in 4.9; users needing them after the
cutover can remain on the final 4.x release. See :doc:`optional-surfaces`.

Use DataFog
===========

.. toctree::
   :maxdepth: 2
   :caption: Use DataFog

   getting-started
   python-sdk
   cli
   optional-surfaces
   important-concepts

Reference
=========

.. toctree::
   :maxdepth: 2
   :caption: Reference

   definitions

Contributing
============

.. toctree::
   :maxdepth: 2
   :caption: Contributing

   contributing
   cla-assistant-operations
   v45-release-readiness
   live-module-map

Planning And History
====================

The pages below document release planning, migration history, and future
direction. They are useful context, but they are secondary to the live
usage path above.

.. toctree::
   :maxdepth: 1
   :caption: Planning and history

   roadmap
   planning-history
