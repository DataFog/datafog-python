==================
DataFog Python SDK
==================

Overview
--------
The primary 4.5 SDK path is lightweight text PII screening through the
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

German locale coverage
----------------------

DataFog 4.5 includes regex-only German structured PII support without adding
dependencies. German VAT IDs and German IBANs are active in the default regex
path. Broader German-only identifiers are opt-in because their raw shapes are
common in ordinary product, ticket, invoice, and order data.

Use ``locales=["de"]`` to enable the broader German set:

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

The opt-in German set currently covers ``DE_TAX_ID``,
``DE_SOCIAL_SECURITY_NUMBER``, ``DE_POSTAL_CODE``,
``DE_PASSPORT_NUMBER``, and ``DE_RESIDENCE_PERMIT_NUMBER``. The default set
also covers ``DE_VAT_ID`` and ``DE_IBAN``.

Optional services
-----------------

OCR and Spark are supported optional surfaces, not the primary 4.5 path:

* Use ``datafog[ocr]`` for local OCR helpers such as ``ImageService`` and
  ``PytesseractProcessor``.
* Use ``datafog[web,ocr]`` when OCR inputs must be downloaded from URLs.
* Use ``datafog[nlp-advanced,ocr]`` for Donut OCR, with the model already
  available locally.
* Use ``datafog[distributed]`` for ``SparkService``.
* Use ``datafog[distributed,nlp]`` plus an installed spaCy model for Spark PII
  UDF helpers.

OCR and Spark are not deprecated. Their broader overhaul is deferred so the
4.5 release can keep the core package tight while preserving existing optional
usage. See :doc:`optional-surfaces` for install notes and limitations.

Definitions
-----------
.. automodule:: datafog.main
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
