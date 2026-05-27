================================
Getting Started With DataFog 4.5
================================

DataFog 4.5 focuses on lightweight text PII screening. A core install should
let you scan and redact common structured PII without installing OCR, Spark,
large NLP models, or middleware integrations.

Install Profiles
================

Core text screening:

.. code-block:: bash

   pip install datafog

Optional extras are explicit:

.. list-table::
   :header-rows: 1

   * - Profile
     - Install command
     - Use when
   * - Core
     - ``pip install datafog``
     - You need regex-based text scanning, redaction, and guardrail helpers.
   * - NLP
     - ``pip install "datafog[nlp]"``
     - You need spaCy-backed named entity recognition.
   * - Advanced NLP
     - ``pip install "datafog[nlp-advanced]"``
     - You need GLiNER-backed named entity recognition.
   * - OCR
     - ``pip install "datafog[ocr]"``
     - You need local image text extraction before PII scanning.
   * - OCR from URLs
     - ``pip install "datafog[web,ocr]"``
     - You need DataFog to download image inputs before OCR.
   * - Spark
     - ``pip install "datafog[distributed]"``
     - You need the optional ``SparkService`` surface.
   * - Everything
     - ``pip install "datafog[all]"``
     - You are developing or deliberately want every optional surface.

Python Usage
============

Use the top-level helpers for the 4.5 core path:

.. code-block:: python

   import datafog

   text = "Contact jane@example.com or call 415-555-1212"

   scan_result = datafog.scan(text, engine="regex")
   print(scan_result.entities)

   redact_result = datafog.redact(text, engine="regex")
   print(redact_result.redacted_text)

   print(datafog.sanitize("Card: 4111-1111-1111-1111"))

Agent-oriented helpers use the same lightweight text path:

.. code-block:: python

   import datafog

   prompt = "My SSN is 123-45-6789"
   scan_result = datafog.scan_prompt(prompt, engine="regex")

   if scan_result.entities:
       print("PII detected before sending the prompt")

   output = "Email me at jane.doe@example.com"
   safe_output = datafog.filter_output(output, engine="regex")
   print(safe_output.redacted_text)

German Structured PII
=====================

German structured PII is country-specific and opt-in, including German VAT IDs
and German IBANs:

.. code-block:: python

   import datafog

   result = datafog.scan("USt-IdNr DE 123456789", engine="regex", locales=["de"])
   print([(entity.type, entity.text) for entity in result.entities])

German identifiers such as ``DE_VAT_ID``, ``DE_IBAN``, ``DE_TAX_ID``,
``DE_SOCIAL_SECURITY_NUMBER``, ``DE_POSTAL_CODE``, ``DE_PASSPORT_NUMBER``, and
``DE_RESIDENCE_PERMIT_NUMBER`` require explicit German locale selection or
explicit ``entity_types`` filtering. This keeps ordinary ticket, SKU, order,
and invoice IDs from becoming default-on false positives.

.. code-block:: python

   text = "Steuer-ID 12345678901 liegt vor."

   print(datafog.scan(text, engine="regex").entities)
   print(datafog.scan(text, engine="regex", locales=["de"]).entities)
   print(datafog.scan(text, engine="regex", entity_types=["DE_TAX_ID"]).entities)

CLI Usage
=========

The CLI core path is text-first:

.. code-block:: bash

   datafog scan-text "Contact jane@example.com"
   datafog redact-text "Contact jane@example.com"
   datafog replace-text "Contact jane@example.com"
   datafog hash-text "Contact jane@example.com"
   datafog redact-text "Steuer-ID 12345678901" --locale de

Image commands are optional. Install ``datafog[ocr]`` for local OCR and
``datafog[web,ocr]`` when the CLI needs to download image inputs.

What 4.5 Is Not
===============

DataFog 4.5 prepares the package for future middleware use cases, but it does
not ship dedicated Sentry, OpenTelemetry, logging-framework, or cloud DLP
adapters. Those integrations are future-facing work built on the same core
text screening path.

Next Pages
==========

* :doc:`python-sdk` documents the Python API surface.
* :doc:`cli` documents command-line usage.
* :doc:`optional-surfaces` documents OCR and Spark install notes.
* :doc:`roadmap` explains how 4.5 leads toward later middleware work.
