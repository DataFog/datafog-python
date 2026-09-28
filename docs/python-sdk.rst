==================
DataFog Python SDK
==================

Overview
--------
The primary SDK path is lightweight text PII screening through the
top-level ``datafog`` helpers. These helpers use the regex engine by default
and do not require OCR, Spark, model downloads, or distributed dependencies.

.. code-block:: python

   import datafog

   text = "Contact jane@example.com or call 415-555-1212"

   scan_result = datafog.scan(text, engine="regex")
   print(scan_result.entities)

   redact_result = datafog.redact(text, engine="regex")
   print(redact_result.redacted_text)

   print(datafog.sanitize(text))

The backward-compatible ``DataFog`` and ``TextService`` classes remain
available for existing users. ``TextService(engine="regex")`` is the
dependency-light service path; ``spacy``, ``gliner``, ``smart``, OCR, and Spark
surfaces require their explicit extras.

4.9.0 compatibility and Core preview
------------------------------------

DataFog 4.9.0 provides an experimental Rust backend and native schema preview.
Existing top-level ``scan``/``redact`` functions retain their
result shapes and use the Python backend by default. They delegate through the
new facade, whose classes are the same objects as the established result types:

.. code-block:: python

   from datafog.compat.v4 import Entity, ScanResult, RedactResult, scan, redact

The facade does not include ``detect`` or ``process``. Those legacy helpers
continue to work at the top level in 4.9 but warn of removal in 5.0, revising the
previous promise to retain them throughout 5.x. Moving from ``process`` to
``redact`` can change old placeholder and hash output; compare results explicitly.

The adapter requires ``datafog-core>=0.4.0,<0.5``. Install with
``python -m pip install --upgrade "datafog[rust]==4.9.0"`` to evaluate Rust.
A base install of ``datafog==4.9.0`` has no native dependency; installing the
extra does not change the default Python backend:

.. code-block:: python

   import datafog

   result = datafog.redact("Contact jane@example.com", engine="regex", backend="rust")
   assert result.redacted_text == "Contact [EMAIL_1]"

``backend`` is keyword-only, defaults to ``python``, and supports Rust only with
``engine="regex"``. Detection uses Core; Python still handles legacy aliases,
full-match allowlists, result conversion, and transformation strategies. Explicit
entities passed to ``redact`` require no native scanning. Missing native modules,
unsupported combinations, and native errors are not silently retried in Python.
The ``DataFog`` class, ``TextService``, CLI, and ML composition keep their existing
backend paths.

The native ``datafog.v5`` preview exposes actual Core types and operations rather
than adapting them to legacy classes:

.. code-block:: python

   from datafog.v5 import Finding, scan, scan_and_transform

   findings = scan("Contact jane@example.com")
   assert isinstance(findings[0], Finding)
   result = scan_and_transform(
       "Contact jane@example.com",
       {"transform": {"default": {"strategy": "redact"}}},
   )
   assert result.text == "Contact [EMAIL]"

Native scanning returns ``list[Finding]`` with ``entity_type``, ``matched_text``,
and explicit offset ranges. Native transformation returns ``TransformResult``
with ``text`` and transformation records. Legacy numbered tokens, plaintext
mappings, and hash/pseudonymization strategies are not interchangeable with
native strategies. Importing the namespace is lazy; accessing its exports
requires the Rust extra. The supported compatibility lifetime after 5.0 remains
a separate decision.

The adapter requires capability contract version 1 and discovers supported labels,
locales, and activation settings from the installed Core. Future finding labels
are preserved. Core 0.4.x updates may change detection output; lock the version
when reproducibility is required. German aliases ``de``, ``de-DE``, and ``de_DE``
activate German detectors; ``en-US`` and ``fr`` activate only base detectors.
Locale validation trims ASCII whitespace and ignores ASCII case; unsupported
explicit locales raise errors. Multiple Python locales produce a deduplicated
union of Core scans. Explicit German entity selection enables the required locale.

Select ``entity_types=["UUID"]`` with ``backend="rust"`` to enable UUID detection
through Core metadata. Core's ``PERSON`` is structured-only and explicitly
selecting it for Rust text scanning raises an error. The Python default backend
keeps its existing behavior.

Core 0.4.0 adds JWT, private-key, contextual routing-number, and contextual NPI
findings. The legacy overlap policy can prefer ``PHONE`` over a same-span ``NPI``;
filtering for NPI then returns no entities. Native ``datafog.v5.scan`` retains NPI,
and native transformation can select it. Legacy result and transformation
semantics remain unchanged.

Read the :download:`complete migration guide <migration-4.9.md>` for the exact
schema comparison, finite-corpus parity results, and verification commands.

German locale coverage
----------------------

The Python backend includes regex-only German structured PII support without adding
dependencies. German-only identifiers are opt-in because their raw shapes are
country-specific or common in ordinary product, ticket, invoice, and order
data.

Use ``locales=["de"]`` to enable the German set:

.. code-block:: python

   import datafog

   text = "Steuer-ID 12345678901 liegt vor."
   result = datafog.scan(text, engine="regex", locales=["de"])
   print([(entity.type, entity.text) for entity in result.entities])

You can also request one German entity type directly:

.. code-block:: python

   result = datafog.scan(
       "Steuer-ID 12345678901 liegt vor.",
       engine="regex",
       entity_types=["DE_TAX_ID"],
   )

The opt-in German set currently covers ``DE_VAT_ID``, ``DE_IBAN``,
``DE_TAX_ID``, ``DE_SOCIAL_SECURITY_NUMBER``, ``DE_POSTAL_CODE``,
``DE_PASSPORT_NUMBER``, and ``DE_RESIDENCE_PERMIT_NUMBER``.

Optional services
-----------------

OCR and Spark remain available as optional surfaces throughout 4.9:

* Use ``datafog[ocr]`` for local OCR helpers such as ``ImageService`` and
  ``PytesseractProcessor``.
* Use ``datafog[web,ocr]`` when OCR inputs must be downloaded from URLs.
* Use ``datafog[nlp-advanced,ocr]`` for Donut OCR, with the model already
  available locally.
* Use ``datafog[distributed]`` for ``SparkService``.
* Use ``datafog[distributed,nlp]`` plus an installed spaCy model for Spark PII
  UDF helpers.

DataFog 4.9.0 deprecates OCR and Spark for removal in 5.0. Use-time
``FutureWarning`` notices are visible under normal Python warning filters. Users
needing these features can remain on the final 4.x release; this migration does
not introduce successor packages or promise indefinite maintenance. See
:doc:`optional-surfaces` for install notes and limitations.

Definitions
-----------
.. automodule:: datafog.main
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
