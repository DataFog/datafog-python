==================
Important Concepts
==================

Overview
--------


Data Models
^^^^^^^^^^^
Existing models support legacy PII annotation and optional OCR analysis.
The 4.9.0 bridge retains them and adds ``datafog.compat.v4`` for the
legacy scan/redact result classes (``Entity``, ``ScanResult``, ``RedactResult``).
``datafog.v5`` separately previews native Core ``Finding`` and ``TransformResult``
objects; these have different fields and transformation semantics. See
:doc:`python-sdk` and the :download:`migration guide <migration-4.9.md>`.

* AnalysisExplanation
* AnnotationResult
* AnnotatorRequest
* EntityTypes
* Pattern
* PatternRecognizer

Processors
^^^^^^^^^^^
Text processors remain available. OCR processors below are deprecated in the
4.9.0 bridge and scheduled for removal in 5.0:

* SpacyAnnotator
    Text annotation with spaCy
* DonutProcessor
    Image processing
* PytesseractProcessor
    OCR

Services
^^^^^^^^^^^
``TextService`` remains available. ``ImageService`` and ``SparkService`` are
optional legacy services, deprecated in 4.9 for removal in 5.0. They remain
functional throughout 4.9; users requiring them after the cutover can remain on
the final 4.x release. See :doc:`optional-surfaces`.

Existing services:

* ImageService
    Image handling and OCR
* SparkService
    PySpark wrapper
* TextService
    PII annotation


Data Models 
-------------------------

.. automodule:: datafog.models.annotator
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   AnnotatorRequest
   AnnotationResult
   AnalysisExplanation

.. automodule:: datafog.models.common
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   EntityTypes
   Pattern
   PatternRecognizer
   AnnotatorMetadata

.. automodule:: datafog.models.spacy_nlp
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   SpacyAnnotator

Processors
-------------------------

.. automodule:: datafog.processing.image_processing.donut_processor
   :members:

.. automodule:: datafog.processing.image_processing.image_downloader
   :members:

.. automodule:: datafog.processing.image_processing.pytesseract_processor
   :members:

.. automodule:: datafog.processing.text_processing.spacy_pii_annotator
   :members:

.. automodule:: datafog.processing.spark_processing.pyspark_udfs
   :members:


Services
-------------------------

.. automodule:: datafog.services.image_service
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   ImageDownloader
   ImageService

.. automodule:: datafog.services.spark_service
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   SparkService


.. automodule:: datafog.services.text_service
   :members:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   TextService
