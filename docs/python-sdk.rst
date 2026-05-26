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
