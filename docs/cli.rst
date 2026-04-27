===========
DataFog CLI
===========

Overview
--------
The main entrypoint for the CLI is through the DataFog client file, defined in :mod:`datafog.client`.
We use Typer to build the CLI, with each command defined as a separate function.

v5 Machine-Readable Commands
----------------------------

The v5 CLI adds ``scan``, ``redact``, and ``audit`` commands with stable JSON
and JSONL output for automation.

Scan text and emit the frozen JSON schema:

.. code-block:: bash

   datafog scan "Email jane@example.com" --json

Redact text and return replacement metadata:

.. code-block:: bash

   datafog redact "Email jane@example.com" --json

Audit a file or directory and fail CI on high-severity findings:

.. code-block:: bash

   datafog audit ./logs --json --fail-on high

For record-oriented workflows, use JSONL:

.. code-block:: bash

   datafog audit ./logs/app.jsonl --jsonl --emit-summary

Exit codes:

* ``0``: clean or successful command.
* ``1``: configured detection threshold was met.
* ``2``: usage or configuration error.
* ``3``: processing error.

See :doc:`v5-rc1-api-contract` for the frozen JSON/JSONL schema.

Definitions
-----------
.. automodule:: datafog.client
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
