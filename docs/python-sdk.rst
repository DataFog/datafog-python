==================
DataFog Python SDK
==================

Overview
--------
The main entrypoint for the SDK is through the DataFog class, defined in :mod:`datafog.main`.
Here you can initialize the different services, including TextService, ImageService, and SparkService.

v5 Custom Recognizers
---------------------

Use ``RegexRecognizer`` for domain-specific identifiers or secrets that are not
part of DataFog's built-in detector set:

.. code-block:: python

   import datafog

   customer_id = datafog.RegexRecognizer(
       entity_type="CUSTOMER_ID",
       pattern=r"CUST-\d{4}",
       confidence=0.92,
       description="Internal customer identifier",
   )

   result = datafog.scan(
       "Customer CUST-1234 opened a ticket",
       recognizers=[customer_id],
   )

Per-call recognizers apply only to that scan/redaction call. Register a
recognizer globally when an application should use it everywhere:

.. code-block:: python

   datafog.register_regex_recognizer(
       entity_type="WORKSPACE_ID",
       pattern=r"ws_[a-z0-9]{6}",
       confidence=0.88,
       description="Workspace identifier",
   )

Validators can reject false positives or attach validation metadata:

.. code-block:: python

   def valid_account(value: str) -> bool:
       return value.endswith("42")

   account_id = datafog.RegexRecognizer(
       entity_type="ACCOUNT_ID",
       pattern=r"ACCT-\d{2}",
       validator=valid_account,
   )

Custom recognizers produce normal v5 ``Entity`` objects and therefore work with
``scan()``, ``redact()``, policies, CLI-safe serialization, and result models.

v5 Streaming Guardrails
-----------------------

Use ``filter_stream()`` for model or tool outputs that arrive as text chunks:

.. code-block:: python

   import datafog

   chunks = ["Contact adm", "in@example", ".com"]

   for safe_chunk in datafog.filter_stream(chunks, engine="regex"):
       print(safe_chunk)
   # Contact [EMAIL_1]

Async streams use ``filter_async_stream()``:

.. code-block:: python

   async for safe_chunk in datafog.filter_async_stream(stream, engine="regex"):
       yield safe_chunk

The v5.0 implementation buffers the stream before emitting filtered output.
That is intentional: emails, access tokens, and provider keys can start in one
chunk and finish in another, and emitting partial raw chunks would leak PII.

Definitions
-----------
.. automodule:: datafog.main
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
