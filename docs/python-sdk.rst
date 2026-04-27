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

Definitions
-----------
.. automodule:: datafog.main
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst
