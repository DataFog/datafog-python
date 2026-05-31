=========================
Optional OCR And Spark
=========================

DataFog 4.5 keeps the core package focused on lightweight text PII screening.
The default path is:

.. code-block:: bash

   pip install datafog

.. code-block:: python

   import datafog

   result = datafog.redact("Email jane@example.com", engine="regex")
   print(result.redacted_text)

OCR and Spark are supported optional surfaces. They are useful for image and
distributed workflows, but they should not be treated as required for the core
install, package import, text scanning, text redaction, or guardrail helpers.

OCR
---

Use OCR when you need to extract text from images before running PII detection.

Install local OCR support:

.. code-block:: bash

   pip install "datafog[ocr]"

Use URL-based image downloads:

.. code-block:: bash

   pip install "datafog[web,ocr]"

Use Donut OCR:

.. code-block:: bash

   pip install "datafog[nlp-advanced,ocr]"

Notes:

* Tesseract usage requires the system ``tesseract`` binary in addition to the
  Python extra.
* Python 3.13 is validated for the OCR install profile, Pillow, pytesseract,
  and system Tesseract smoke checks.
* Donut OCR requires a model that is already available locally. DataFog should
  not download models implicitly during normal runtime usage.
* OCR is not deprecated. A broader OCR API and packaging overhaul is deferred
  beyond the 4.5 focus release.

Example local OCR flow:

.. code-block:: python

   import asyncio
   from datafog.services.image_service import ImageService

   async def main():
       service = ImageService(use_tesseract=True, use_donut=False)
       extracted = await service.ocr_extract(["./invoice.png"])
       print(extracted)

   asyncio.run(main())

Spark
------

Use Spark when you need distributed processing around DataFog PII detection.

Install Spark support:

.. code-block:: bash

   pip install "datafog[distributed]"

Use Spark PII UDF helpers:

.. code-block:: bash

   pip install "datafog[distributed,nlp]"

Notes:

* ``SparkService`` requires PySpark and a Java runtime.
* Spark PII UDF helpers also require spaCy and an installed spaCy model.
* Spark is not deprecated. A broader Spark overhaul is deferred beyond the 4.5
  focus release.

Example local Spark flow:

.. code-block:: python

   from datafog.services.spark_service import SparkService

   service = SparkService(master="local[1]")
   rows = service.read_json("./records.json")
   print(rows)

Core-path verification
----------------------

The repository includes tests that block optional dependency imports while
importing ``datafog`` and running the default text helpers. These checks verify
that OCR, Spark, NLP, model-loading, and web dependencies are not required for
the core path.

Python 3.13 optional-profile status
-----------------------------------

DataFog 4.5 validates Python 3.13 beyond the core/CLI path for the optional
profiles that currently have compatible wheels in the tested dependency set.

.. list-table::
   :header-rows: 1

   * - Profile
     - Python 3.13 status
     - Notes
   * - ``nlp``
     - Supported
     - spaCy imports and the profile smoke test pass on Python 3.13.
   * - ``nlp-advanced``
     - Supported
     - GLiNER, torch, transformers, and onnxruntime import successfully on
       Python 3.13.
   * - ``ocr``
     - Supported
     - Pillow, pytesseract, and the system Tesseract bridge validate on Python
       3.13 when the ``tesseract`` binary is installed.
   * - ``nlp-advanced,ocr``
     - Supported with local model requirement
     - Donut dependencies import on Python 3.13; runtime OCR still requires the
       configured Donut model to be present locally.
   * - ``distributed`` and ``all``
     - Not newly certified in 4.5
     - Keep using Python 3.10-3.12 for distributed/all-profile validation until
       Spark and the full optional surface are audited separately.
