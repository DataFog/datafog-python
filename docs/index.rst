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

4.10.0 native default
=====================

DataFog 4.10.0 turns the native engine on by default. ``pip install datafog``
now installs ``datafog-core``, and detection uses it whenever it imports; the
pure-Python engine remains the fallback and ``DATAFOG_BACKEND=python`` forces
it. No public API is removed in 4.10.0 and no existing call changes shape — the
``backend`` keyword is still accepted, and now also accepts ``auto``.

:download:`Complete 4.10 migration guide <migration-4.10.md>`.

Prose ``PERSON`` and ``ADDRESS`` detection now comes from an embedded model, so
names and addresses no longer need spaCy or a model download. The native engine
adds credential, account and German detectors. Reviewed differences from the
Python engine are recorded in ``tests/contracts/rust-1.2.0.json`` and the
migration guide below.

4.9.0 migration bridge
======================

DataFog 4.9.0 was the migration bridge to the Rust-backed 5.0 API. It added the
explicit ``backend="rust"`` opt-in, the ``datafog.compat.v4`` facade and the
``datafog.v5`` preview. 4.10.0 built on it by making the native path the
default.

4.9 preserves existing imports, result classes, Python detection defaults, and
redaction behavior. It adds explicit experimental Rust detection through
``backend="rust"``, the ``datafog.compat.v4`` facade, and the ``datafog.v5`` native
Core schema preview. See :doc:`python-sdk` and the
:download:`complete 4.9 migration guide <migration-4.9.md>`.

DataFog 4.9.0 deprecates ``detect()``/``process()``, OCR, and Spark for
removal in 5.0. The earlier promise to retain ``detect()``/``process()`` throughout
5.x is revised. OCR/Spark remain functional in 4.9; users needing them after the
cutover can pin :doc:`retirement`.

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
   retirement

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
