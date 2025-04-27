===========
Important Concepts
===========

Overview
--------


Data Models
^^^^^^^^^^^
Key data models to support PII annotation and OCR analysis.

* AnalysisExplanation
* AnnotationResult
* AnnotatorRequest
* EntityTypes
* Pattern
* PatternRecognizer

Processors
^^^^^^^^^^^
Main processors:
* SpacyAnnotator
    Text annotation with spaCy
* DonutProcessor
    Image processing
* PytesseractProcessor
    OCR

Services
^^^^^^^^^^^
Core services:
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

# .. automodule:: datafog.processing.spark_processing.pyspark_udfs
#    :members:
#    :undoc-members:


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
