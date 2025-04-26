"""
PySpark UDFs for PII annotation and related utilities.

This module provides functions for PII (Personally Identifiable Information) annotation
using SpaCy models in a PySpark environment. It includes utilities for installing
dependencies, creating and broadcasting PII annotator UDFs, and performing PII annotation
on text data.
"""

import importlib
import logging
import subprocess
import sys
import traceback
from typing import List

try:
    import spacy
except ImportError:
    print("Spacy not found. Please install it: pip install spacy")
    print("and download the model: python -m spacy download en_core_web_lg")
    spacy = None
    traceback.print_exc()
    sys.exit(1)

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf
    from pyspark.sql.types import ArrayType, StringType
except ImportError:
    print(
        "PySpark not found. Please install it with the [spark] extra: pip install 'datafog[spark]'"
    )

    # Set placeholders to allow module import even if pyspark is not installed
    def placeholder_udf(*args, **kwargs):
        return None

    def placeholder_arraytype(x):
        return None

    def placeholder_stringtype():
        return None

    udf = placeholder_udf
    ArrayType = placeholder_arraytype
    StringType = placeholder_stringtype
    SparkSession = None  # Define a placeholder
    traceback.print_exc()
    # Do not exit, allow basic import but functions using Spark will fail later if called

from datafog.processing.text_processing.spacy_pii_annotator import pii_annotator

PII_ANNOTATION_LABELS = ["DATE_TIME", "LOC", "NRP", "ORG", "PER"]
MAXIMAL_STRING_SIZE = 1000000


def broadcast_pii_annotator_udf(
    spark_session=None, spacy_model: str = "en_core_web_lg"
):
    """Broadcast PII annotator across Spark cluster and create UDF"""
    if not spark_session:
        spark_session = SparkSession.builder.getOrCreate()  # noqa: F821
    broadcasted_nlp = spark_session.sparkContext.broadcast(spacy.load(spacy_model))

    pii_annotation_udf = udf(
        lambda text: pii_annotator(text, broadcasted_nlp),
        ArrayType(ArrayType(StringType())),
    )
    return pii_annotation_udf
