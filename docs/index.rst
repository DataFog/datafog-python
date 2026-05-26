=====================
DataFog Documentation
=====================

DataFog is an open-source tool for lightweight text PII detection and
anonymization. The core install focuses on fast regex-based scanning and
redaction, with optional extras for NLP, OCR, and Spark-style workflows.

.. toctree::
   :maxdepth: 2

   important-concepts
   cli
   python-sdk
   optional-surfaces
   definitions
   roadmap
   v44-bridge-release
   v5-product-brief
   v5-compatibility-matrix
   v5-cut-line

=====================
Getting Started
=====================

Installation
------------

Install the lightweight text screening core via pip:

.. code-block:: bash

    pip install datafog

Optional extras such as ``nlp``, ``nlp-advanced``, ``ocr``, ``distributed``,
and ``web`` are installed only when you need those surfaces.

---------------------
CLI Usage
---------------------

For a list of available operations, run:

.. code-block:: bash

    datafog --help

Scan text for PII:

.. code-block:: bash

    datafog scan-text "Your text here"

Image/OCR commands are optional. Local OCR requires ``datafog[ocr]``; URL-based
image downloading requires ``datafog[web,ocr]``.

.. code-block:: bash

    datafog scan-image "path/to/image.png" --operations extract

Scan for PII in image text:

.. code-block:: bash

    datafog scan-image "path/to/image.png" --operations scan

For more information on optional OCR and Spark surfaces, see
:doc:`optional-surfaces`.

---------------------
Python SDK Usage
---------------------

Scan text for PII:

.. code-block:: python

   
   import datafog

   text = "Contact jane@example.com or call 415-555-1212"
   result = datafog.scan(text, engine="regex")
   print(result.entities)
   print(datafog.redact(text, engine="regex").redacted_text)

Run OCR and then scan extracted text only when the OCR extra is installed:

.. code-block:: python

   
   import asyncio
   from datafog import DataFog

   # For OCR and PII annotation
   ocr_client = DataFog(operations="extract,scan")

   async def run_ocr_pipeline_demo():
       image_url = "https://s3.amazonaws.com/thumbnails.venngage.com/template/dc377004-1c2d-49f2-8ddf-d63f11c8d9c2.png"
       results = await ocr_client.run_ocr_pipeline(image_urls=[image_url])
       print("OCR Pipeline Results:", results)

   # Run the async function
   asyncio.run(run_ocr_pipeline_demo())

For detailed information on the Python SDK, see :doc:`python-sdk`.
