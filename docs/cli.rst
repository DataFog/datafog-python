===========
DataFog CLI
===========

Overview
--------
The main entrypoint for the CLI is through the DataFog client file, defined in :mod:`datafog.client`.
We use Typer to build the CLI, with each command defined as a separate function.

Core text commands such as ``scan-text``, ``redact-text``, ``replace-text``,
and ``hash-text`` are the primary CLI path. The 4.9.0 bridge leaves text commands on their
existing Python detection paths; the opt-in Rust backend is a Python API option,
not a new CLI flag. Install ``datafog[cli]`` for the command-line dependencies.

OCR commands remain functional in 4.9 but are deprecated for removal in 5.0.
``scan-image`` emits a visible ``FutureWarning`` at use time. Its optional
dependencies are:

* Local image OCR requires ``datafog[ocr]`` and any needed system OCR binaries
  such as Tesseract.
* URL-based image OCR also requires ``datafog[web,ocr]``.
* Donut OCR requires ``datafog[nlp-advanced,ocr]`` and a local model.

Spark/distributed workflows are Python SDK surfaces rather than first-path CLI
commands. Spark support is also deprecated in 4.9 for removal in 5.0. Install
``datafog[distributed]`` when using ``SparkService`` during 4.x. Users needing
OCR/Spark after the cutover can remain on the final 4.x release. See
:doc:`optional-surfaces` and the
:download:`4.9 migration guide <migration-4.9.md>`.

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
