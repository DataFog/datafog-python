=====================
DataFog Documentation
=====================

DataFog is an open-source tool for PII detection and anonymization of unstructured data. This documentation covers the CLI and Python SDK.

.. toctree::
   :maxdepth: 2

   important-concepts
   cli
   python-sdk
   definitions
   roadmap

=====================
Getting Started
=====================

---------------------
Installation

Install DataFog via pip:

.. code-block:: bash

    pip install datafog

This installs the latest stable version with CLI support.

---------------------
CLI Usage
---------------------

For a list of available operations, run:

.. code-block:: bash

    datafog --help

Scan text for PII:

.. code-block:: bash

    datafog scan-text "Your text here"

Extract text from image:

.. code-block:: bash

    datafog scan-image "path/to/image.png" --operations extract

Scan for PII in image:

.. code-block:: bash

    datafog scan-image "path/to/image.png" --operations scan

For more information on the CLI, see :doc:`cli`.

---------------------
Python SDK Usage
---------------------

Scan text for PII:

.. code-block:: python

   
   import requests
   from datafog import DataFog

   # For text annotation
   client = DataFog(operations="scan")

   # Fetch sample medical record
   doc_url = "https://gist.githubusercontent.com/sidmohan0/b43b72693226422bac5f083c941ecfdb/raw/b819affb51796204d59987893f89dee18428ed5d/note1.txt"
   response = requests.get(doc_url)
   text_lines = [line for line in response.text.splitlines() if line.strip()]

   # Run annotation
   annotations = client.run_text_pipeline_sync(str_list=text_lines)
   print(annotations)
    
Scan image for PII:

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


