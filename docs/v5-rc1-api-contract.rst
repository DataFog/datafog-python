=======================
v5 RC1 API Contract
=======================

Status
------

RC1 API-freeze draft for DataFog Python v5.0.0.

Release Posture
---------------

v5.0 should be built as a GA-shaped beta:

* ``5.0.0b1`` is the public beta for the new local-first API.
* ``5.0.0rc1`` freezes core contracts.
* ``5.0.0`` is the polished GA for the core API, not every integration.

The guiding rule is:

   Core path must feel GA. Surface area can be beta.

The following surfaces are trust-critical and must be stable before RC1:

* ``pip install datafog``
* ``import datafog``
* ``datafog.scan(...)``
* ``datafog.redact(...)``
* ``datafog.protect(...)``
* ``datafog.restore(...)``
* No-network-by-default behavior.
* No implicit model downloads.
* Safe metadata by default.
* Typed result objects.
* Basic CLI ``scan``, ``redact``, and ``audit`` commands.

Experimental v5.0 beta surfaces may include:

* OpenTelemetry recipes or adapters.
* LangSmith and Langfuse recipes or adapters.
* FastAPI recipes.
* Advanced policy presets.
* Custom recognizer registry details.
* Streaming guardrails.
* PERSON, ORGANIZATION, LOCATION, and ADDRESS NLP detection.
* Dataset summary UX.

Model Contract
--------------

Runtime result models should be dataclasses. Policy, config, and user-supplied
configuration can use Pydantic. JSON and CLI output must use explicit safe
serializers rather than relying on automatic model dumps.

ValidationResult
~~~~~~~~~~~~~~~~

Freeze the public fields:

.. code-block:: python

   @dataclass(frozen=True, slots=True)
   class ValidationResult:
       validator: str
       status: Literal[
           "valid",
           "invalid",
           "unknown",
           "not_applicable",
           "region_required",
           "checksum_failed",
           "parse_failed",
       ]
       reason: str | None = None

Do not expose normalized raw values here by default. Normalized emails, phone
numbers, card fragments, tokens, and identifiers may still be sensitive.

Entity
~~~~~~

Freeze the public fields:

.. code-block:: python

   @dataclass(frozen=True, slots=True)
   class Entity:
       type: str
       start: int
       end: int
       confidence: float
       severity: Literal["low", "medium", "high", "critical"]
       detector: str
       validation: ValidationResult | None = None
       text: str | None = None

Field semantics:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Meaning
   * - ``type``
     - Canonical uppercase entity type, such as ``EMAIL``, ``SSN``, or
       ``API_KEY``.
   * - ``start``
     - Start character offset in the original input.
   * - ``end``
     - Exclusive end character offset in the original input.
   * - ``confidence``
     - Detection confidence from ``0.0`` to ``1.0``.
   * - ``severity``
     - Risk if the detection is true. This is not confidence.
   * - ``detector``
     - Detector ID, such as ``regex.email`` or
       ``validator.credit_card_luhn``.
   * - ``validation``
     - Optional validation result.
   * - ``text``
     - Raw matched text only when explicitly allowed.

``severity`` and ``confidence`` are intentionally separate. A credit card can
be critical severity with 0.80 confidence. An email can be high severity with
1.0 confidence.

ScanResult
~~~~~~~~~~

Freeze the public fields:

.. code-block:: python

   @dataclass(frozen=True, slots=True)
   class ScanResult:
       entities: list[Entity]
       input_length: int
       engine: str
       locale: str
       policy_name: str | None = None
       include_text: bool = False

``ScanResult`` must not include the full original input text. Scan results are
easy to log accidentally, so v5 should keep only safe metadata by default.

Replacement
~~~~~~~~~~~

Add a public replacement model for redaction metadata:

.. code-block:: python

   @dataclass(frozen=True, slots=True)
   class Replacement:
       entity_index: int
       action: Literal["token", "mask", "hmac", "drop", "block", "warn"]
       original_start: int
       original_end: int
       replacement_start: int
       replacement_end: int
       replacement: str | None = None
       token: str | None = None

``Replacement`` must not include raw original values.

RedactResult
~~~~~~~~~~~~

Freeze the public fields:

.. code-block:: python

   @dataclass(frozen=True, slots=True)
   class RedactResult:
       redacted_text: str
       entities: list[Entity]
       replacements: list[Replacement]
       policy_name: str | None = None
       session_id: str | None = None

``RedactResult`` must not expose raw mappings by default. Mappings belong
inside an explicit ``TokenSession``.

TokenSession
~~~~~~~~~~~~

Freeze the public fields and defaults:

.. code-block:: python

   @dataclass(slots=True)
   class TokenSession:
       session_id: str
       token_scope: Literal["value", "occurrence"] = "value"
       token_prefix: str = "DF"

Internal private state:

.. code-block:: python

   _token_to_value: dict[str, str]
   _value_to_token: dict[tuple[str, str], str]
   _counters: dict[str, int]

Public safe methods and properties:

.. code-block:: python

   session.mapping_count
   session.to_safe_dict()
   session.clear()

Persistent token mapping export is out of scope for v5.0. If an unsafe export
method is ever added, it must be named explicitly, for example
``export_unsafe_mapping()``.

Raw Text Policy
---------------

Raw detected text is excluded by default.

.. code-block:: python

   result = datafog.scan("Email john@example.com")
   result.entities[0].text
   # None

Per-call raw text opt-in is allowed:

.. code-block:: python

   result = datafog.scan("Email john@example.com", include_text=True)
   result.entities[0].text
   # "john@example.com"

Policy and environment settings may deny raw text. There should be no global
setting that enables raw text.

Precedence:

.. code-block:: text

   global deny > policy deny > per-call include_text=True > default false

Supported global deny:

.. code-block:: bash

   DATAFOG_DISABLE_RAW_TEXT=1

Do not support a global ``DATAFOG_INCLUDE_RAW_TEXT`` setting.

Severity Defaults
-----------------

Severity means risk if the detection is true. It is not confidence.

P0 default severities:

.. list-table::
   :header-rows: 1
   :widths: 40 20

   * - Entity type
     - Default severity
   * - ``CREDIT_CARD``
     - ``critical``
   * - ``SSN``
     - ``critical``
   * - ``API_KEY``
     - ``critical``
   * - ``SECRET``
     - ``critical``
   * - ``ACCESS_TOKEN``
     - ``critical``
   * - ``PRIVATE_KEY``
     - ``critical``
   * - ``PASSWORD``
     - ``critical``
   * - ``EMAIL``
     - ``high``
   * - ``PHONE``
     - ``high``
   * - ``IP_ADDRESS``
     - ``high``
   * - ``URL``
     - ``medium``
   * - ``UUID``
     - ``medium``

P1 or contextual severities:

.. list-table::
   :header-rows: 1
   :widths: 40 20

   * - Entity type
     - Default severity
   * - ``DATE_OF_BIRTH``
     - ``high``
   * - ``DATE``
     - ``low`` or ``medium``
   * - ``ZIP_CODE``
     - ``medium``
   * - ``ADDRESS``
     - ``high``
   * - ``PERSON``
     - ``medium``
   * - ``ORGANIZATION``
     - ``low``
   * - ``LOCATION``
     - ``low``
   * - ``IBAN``
     - ``critical``
   * - ``BANK_ACCOUNT``
     - ``critical``
   * - ``CRYPTO_WALLET``
     - ``high``

``IP_ADDRESS`` severity may be lowered after validation:

* Public IP: ``high``.
* Private/internal IP: ``medium``.
* Loopback or link-local IP: ``low`` or ``medium``.

Hashing Contract
----------------

Canonical public strategy:

.. code-block:: text

   hmac

Ergonomic alias:

.. code-block:: text

   hash

``hash`` must mean HMAC-SHA256, never plain SHA. Optional explicit alias:
``hmac_sha256``.

Supported examples:

.. code-block:: python

   datafog.redact(text, strategy="hmac", hash_key=key)
   datafog.redact(text, strategy="hash", hash_key=key)

If a user requests hashing without a key, raise:

.. code-block:: text

   Hash strategy requires an HMAC key. Supply hash_key=...,
   DATAFOG_HMAC_KEY, or use strategy="token".

Plain SHA hashing is not recommended. If retained for non-security use cases,
it must be named loudly, for example ``sha256_unsafe``.

P0 Recognizers
--------------

P0 structured PII:

* ``EMAIL``
* ``PHONE``
* ``IP_ADDRESS``
* ``SSN``
* ``CREDIT_CARD``
* ``URL``
* ``UUID``

P0 secrets and developer leakage:

* ``API_KEY``
* ``SECRET``
* ``ACCESS_TOKEN``
* ``PRIVATE_KEY``
* ``PASSWORD``
* ``JWT``
* ``BEARER_TOKEN``

P0 provider-specific patterns if easy:

* ``AWS_ACCESS_KEY_ID``
* ``GITHUB_TOKEN``
* ``OPENAI_API_KEY``
* ``ANTHROPIC_API_KEY``
* ``GOOGLE_API_KEY``
* ``HUGGINGFACE_TOKEN``
* ``COHERE_API_KEY``
* ``MISTRAL_API_KEY``
* ``GROQ_API_KEY``
* ``TOGETHER_API_KEY``
* ``PERPLEXITY_API_KEY``
* ``XAI_API_KEY``
* ``AZURE_OPENAI_API_KEY``
* ``SLACK_TOKEN``
* ``STRIPE_KEY``

Provider-specific recognizers should prefer exact public prefixes when the
provider documents or exposes a stable prefix. Otherwise they should detect
common environment variable and config key names, such as
``ANTHROPIC_API_KEY`` or ``GEMINI_API_KEY``, without pretending the underlying
secret format is stable.

PERSON, ORGANIZATION, LOCATION, and ADDRESS are optional advanced/NLP scope,
not part of the v5.0 core guarantee.

DATE, DOB, and ZIP Scope
------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 30

   * - Detector
     - Scope
   * - Generic ``DATE``, such as ``2026-04-27``
     - P1
   * - Contextual ``DATE_OF_BIRTH``, such as ``DOB: 04/27/1980``
     - P0
   * - Generic ``ZIP_CODE``, such as ``94105``
     - P1
   * - Contextual ZIP or postal code
     - P1 for v5.0

Generic dates and ZIP codes should not fail CLI audit by default unless the
user selects strict behavior or explicitly includes those entity types.

Phone Locale Contract
---------------------

Default locale is ``global``. E.164 and international numbers can validate
confidently. National-format numbers should be detected as candidates and
marked ``region_required`` unless a region is supplied.

Examples:

.. code-block:: python

   datafog.scan(text)
   datafog.scan(text, locale="global")
   datafog.scan(text, locale="us")
   datafog.scan(text, phone_region="US")

Tokenization Contract
---------------------

Reversible restore is in-memory only for v5.0. No file persistence, SQLite
vault, hosted vault, automatic session export, or raw mapping written to disk.

Repeated identical values should receive the same token within a session by
default:

.. code-block:: python

   session = datafog.TokenSession()
   datafog.redact(
       "Email sid@example.com, then sid@example.com again",
       session=session,
   )
   # "Email [EMAIL_1], then [EMAIL_1] again"

Token identity is keyed by ``(entity_type, canonicalized_value)``.

Per-occurrence tokenization is opt-in:

.. code-block:: python

   session = datafog.TokenSession(token_scope="occurrence")

There is no cross-session stability unless the user explicitly reuses the same
session.

CLI JSON Contract
-----------------

Freeze JSON and JSONL schemas at RC1. Human-readable output may keep improving
after RC1.

Every JSON response includes:

.. code-block:: json

   {
     "schema_version": "datafog.cli.v1",
     "command": "scan",
     "ok": true,
     "input": {},
     "policy": {},
     "summary": {},
     "errors": []
   }

Common top-level fields:

.. list-table::
   :header-rows: 1
   :widths: 24 18 58

   * - Field
     - Type
     - Meaning
   * - ``schema_version``
     - string
     - Schema identifier, for example ``datafog.cli.v1``.
   * - ``command``
     - string
     - ``scan``, ``redact``, or ``audit``.
   * - ``ok``
     - boolean
     - Whether the command executed successfully.
   * - ``input``
     - object
     - Source metadata. Never raw input text.
   * - ``policy``
     - object
     - Effective policy metadata.
   * - ``summary``
     - object
     - Counts and severity summary.
   * - ``errors``
     - array
     - Non-fatal or fatal errors.

Entity JSON schema:

.. code-block:: json

   {
     "type": "EMAIL",
     "start": 6,
     "end": 22,
     "confidence": 1.0,
     "severity": "high",
     "detector": "regex.email",
     "validation": {
       "validator": "email",
       "status": "valid",
       "reason": null
     },
     "text": null
   }

``text`` exists but is ``null`` unless raw text was explicitly requested and
not blocked by policy.

``datafog scan --json`` shape:

.. code-block:: json

   {
     "schema_version": "datafog.cli.v1",
     "command": "scan",
     "ok": true,
     "input": {
       "source": "stdin",
       "path": null,
       "bytes": 42,
       "records": null
     },
     "policy": {
       "preset": "default",
       "locale": "global",
       "include_text": false
     },
     "summary": {
       "entity_count": 1,
       "by_type": {
         "EMAIL": 1
       },
       "by_severity": {
         "high": 1
       },
       "highest_severity": "high"
     },
     "entities": [],
     "errors": []
   }

``datafog redact --json`` adds:

.. code-block:: json

   {
     "redacted_text": "Email [EMAIL_1]",
     "replacements": [
       {
         "entity_index": 0,
         "action": "token",
         "original_start": 6,
         "original_end": 22,
         "replacement_start": 6,
         "replacement_end": 15,
         "replacement": "[EMAIL_1]",
         "token": "[EMAIL_1]"
       }
     ],
     "session": {
       "session_id": null,
       "reversible": false,
       "mapping_count": 0
     }
   }

``datafog audit --json`` adds:

.. code-block:: json

   {
     "exit_code": 1,
     "findings": [
       {
         "path": "./logs/app.jsonl",
         "line": 18,
         "record_index": 17,
         "field": "message",
         "entity": {}
       }
     ]
   }

For ``--jsonl``, each line should be one record-level object:

.. code-block:: json

   {
     "schema_version": "datafog.cli.record.v1",
     "command": "audit",
     "path": "./logs/app.jsonl",
     "line": 18,
     "record_index": 17,
     "field": "message",
     "summary": {
       "entity_count": 1,
       "highest_severity": "high"
     },
     "entities": []
   }

Emit a summary JSONL record only when requested with ``--emit-summary``:

.. code-block:: json

   {
     "schema_version": "datafog.cli.summary.v1",
     "command": "audit",
     "summary": {
       "records_scanned": 2401,
       "entity_count": 18,
       "highest_severity": "critical"
     }
   }

Compatibility Build Strategy
----------------------------

Use the existing repository and package name. Build a clean v5 core, then make
legacy APIs thin compatibility shims around that core. Old internals should be
deleted or moved behind compatibility boundaries over time.

Implementation direction:

.. code-block:: text

   existing repo / package name
       ->
   new v5 core built cleanly
       ->
   legacy APIs become thin compatibility shims
       ->
   old internals get deleted or moved behind compat over time

Compatibility shims should remain through the v5.x line and warn on use, not
on import. Removal should happen no earlier than v6.0.

Final RC1 Decision List
-----------------------

* Freeze ``Entity`` with ``type``, ``start``, ``end``, ``confidence``,
  ``severity``, ``detector``, ``validation``, and ``text``.
* Freeze ``ValidationResult`` with ``validator``, ``status``, and ``reason``.
* Freeze ``ScanResult`` with ``entities``, ``input_length``, ``engine``,
  ``locale``, ``policy_name``, and ``include_text``.
* Add ``Replacement`` with entity index, action, original and replacement
  spans, replacement, and token.
* Freeze ``RedactResult`` with ``redacted_text``, ``entities``,
  ``replacements``, ``policy_name``, and ``session_id``.
* Keep ``TokenSession`` in-memory for v5.0 with
  ``token_scope="value"`` by default.
* Make ``include_text`` per-call opt-in; policy and global settings may block
  it.
* Treat severity as risk-if-true, not confidence.
* Make ``hmac`` the canonical hash strategy and ``hash`` an alias for HMAC.
* Guarantee structured PII and secrets in P0; keep NLP entities optional.
* Defer generic ``DATE`` and ``ZIP_CODE`` to P1. Keep contextual DOB as P0.
* Reuse the same token for repeated identical values in a session by default.
* Freeze CLI JSON and JSONL schemas at RC1.
