v5 Policy Presets
=================

DataFog v5 uses dataclasses for runtime results and Pydantic models for policy
and configuration boundaries. Policies are safe by default: raw detected text is
not returned unless a call explicitly asks for it and policy/global settings
allow it.

Policy Model
------------

``RedactionPolicy`` controls scan filtering and redaction behavior:

.. code-block:: python

   import datafog

   policy = datafog.RedactionPolicy(
       name="support-logs",
       default_action="hmac",
       entity_types={"EMAIL", "PHONE", "API_KEY"},
       threshold=0.8,
       raw_text_mode="deny",
       mapping_mode="none",
   )

   result = datafog.redact(
       "Email jane@example.com",
       policy=policy,
       hash_key="dev-only-example-key",
   )

Supported policy fields:

* ``name``: policy name included in result metadata.
* ``default_action``: one of ``token``, ``mask``, ``hmac``, ``drop``,
  ``block``, or ``warn``.
* ``entity_types``: optional allowlist of canonical entity types.
* ``threshold``: minimum confidence from ``0.0`` to ``1.0``.
* ``locale``: default ``global``.
* ``phone_region``: optional phone region such as ``US``.
* ``raw_text_mode``: ``allow`` or ``deny``.
* ``mapping_mode``: ``none`` or ``session``.
* ``entities``: per-entity overrides with ``action``, ``threshold``, and
  ``enabled``.

Built-In Presets
----------------

``default``
   General-purpose local redaction. Uses ``token`` replacements and allows
   per-call raw text opt-in.

``llm``
   Prompt/output protection. Uses ``token`` replacements and denies raw text in
   result metadata.

``logs``
   Log and trace protection. Uses ``hmac`` replacements and denies raw text.
   HMAC requires ``hash_key=...`` or ``DATAFOG_HMAC_KEY``.

``strict``
   Blocking policy. Raises when matching entities are detected and denies raw
   text.

``dataset``
   Dataset cleanup. Uses ``mask`` replacements and denies raw text.

Raw Text Controls
-----------------

Raw text follows this precedence:

.. code-block:: text

   global deny > policy deny > per-call include_text=True > default false

Use the environment variable below to deny raw matched values everywhere:

.. code-block:: bash

   export DATAFOG_DISABLE_RAW_TEXT=1

There is intentionally no environment variable that globally enables raw text.

Per-Entity Overrides
--------------------

Policies can override action and thresholds by entity type:

.. code-block:: python

   policy = datafog.RedactionPolicy(
       default_action="mask",
       entities={
           "API_KEY": datafog.EntityPolicy(action="block"),
           "EMAIL": datafog.EntityPolicy(action="hmac", threshold=0.9),
       },
   )

Session Mapping
---------------

Reversible token mappings are in-memory only for v5.0:

.. code-block:: python

   session = datafog.TokenSession()
   policy = datafog.RedactionPolicy(mapping_mode="session")

   redacted = datafog.redact(
       "Email jane@example.com",
       policy=policy,
       session=session,
   )

   restored = datafog.restore(redacted.redacted_text, session=session)

``TokenSession.to_safe_dict()`` exposes only metadata and mapping counts, never
raw mappings.
