===================
Retirement schedule
===================

This page is the standing record of surfaces DataFog is removing. It is updated
once per release, and a row is added in the MINOR that deprecates the surface —
never retroactively.

Ordering and removal rules are defined in
`VERSIONING.md <https://github.com/DataFog/datafog-python/blob/main/VERSIONING.md>`__.

Removed or scheduled
====================

.. list-table::
   :header-rows: 1

   * - Surface
     - Last supported version
     - Replacement
     - Removed in
     - Deprecated in
   * - ``OCRMService``
     - ``4.12.0``
     - none
     - ``5.0.0``
     - ``4.9.0``
   * - ``DonutProcessor``
     - ``4.12.0``
     - none
     - ``5.0.0``
     - ``4.9.0``
   * - ``[ocr]`` extra (Donut, Tesseract, Pillow)
     - ``4.12.0``
     - none
     - ``5.0.0``
     - ``4.9.0``
   * - ``[distributed]`` extra (PySpark, pandas)
     - ``4.12.0``
     - :ref:`spark-recipe`
     - ``5.0.0``
     - ``4.9.0``
   * - ``detect()``
     - ``4.12.0``
     - ``scan()``
     - ``5.0.0``
     - ``4.9.0``
   * - ``process()``
     - ``4.12.0``
     - ``redact()``
     - ``5.0.0``
     - ``4.9.0``

After the 4.12.0 release is published, installing ``pip install "datafog==4.12.0"`` keeps every row above working.
That version stays installable on PyPI permanently.

OCR
===

There is no successor package and no 5.x reimplementation. OCR quality was never
the reason anyone adopted DataFog, and a mediocre replacement is worse than a
pin.

.. code-block:: bash

   pip install "datafog[ocr]==4.12.0"

If you need continued OCR support beyond that, stay on ``4.12.0``. Track the
surfaces you depend on by name, not by staying on a major version range, so a
lock file review shows the pin.

.. _spark-recipe:

Spark
=====

No distributed API ships in 5.0. Partition the dataframe and call ``scan`` per
partition: one Spark job with a ``mapInPandas`` step, or Dask's
``map_partitions``. Both run the local engine and need no plugin.

.. code-block:: python

   # Spark
   def scan_partition(rows):
       for pdf in rows:
           pdf["findings"] = pdf["text"].map(lambda t: len(datafog.scan(t)))
           yield pdf

   df.mapInPandas(scan_partition, schema="text string, findings long")

.. code-block:: python

   # Dask
   ddf["findings"] = ddf["text"].map_partitions(
       lambda s: s.map(lambda t: len(datafog.scan(t)))
   )

Per-partition ``scan`` is a pure local call with no network and no shared state,
so worker fan-out is just normal framework behaviour. What you lose versus
``SparkService`` is the UDF packaging, not correctness.

detect and process
==================

``detect()`` and ``process()`` were the pre-4.0 entry points.
``process(anonymize=True)`` used older placeholder and hash semantics, so
migrating to ``redact()`` can intentionally change output. Read the output
before you commit the change.

DataFog Core
============

``datafog-core`` retires surfaces on its own schedule, documented in that
repository. The Python surface here inherits Core's ``contract_version``; a
contract bump is a Core MAJOR and raises the floor in ``datafog`` accordingly.
