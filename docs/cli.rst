===========
DataFog CLI
===========

Overview
--------
The main entrypoint for the CLI is through the DataFog client file, defined in :mod:`datafog.client`.
We use Typer to build the CLI, with each command defined as a separate function.

Core text commands such as ``scan-text``, ``redact-text``, ``replace-text``,
and ``hash-text`` are the primary 4.5 CLI path. OCR commands remain available
for existing users, but they are optional:

* Local image OCR requires ``datafog[ocr]`` and any needed system OCR binaries
  such as Tesseract.
* URL-based image OCR also requires ``datafog[web,ocr]``.
* Donut OCR requires ``datafog[nlp-advanced,ocr]`` and a local model.

Spark/distributed workflows are Python SDK surfaces rather than first-path CLI
commands. Install ``datafog[distributed]`` when using ``SparkService``.

German locale support
---------------------

German structured PII is opt-in through ``--locale de`` on the core text
commands:

.. code-block:: bash

   datafog scan-text "Steuer-ID 12345678901" --locale de
   datafog redact-text "Passnummer C12345678" --locale de

Definitions
-----------
.. automodule:: datafog.client
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
