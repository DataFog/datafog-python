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


def pii_annotator(text: str, broadcasted_nlp) -> list[list[str]]:
    """Extract features using en_core_web_lg model.

    Returns:
        list[list[str]]: Values as arrays in order defined in the PII_ANNOTATION_LABELS.
    """
    # ensure_installed("pyspark")
    # ensure_installed("spacy")
    import spacy

    # from pyspark.sql import SparkSession
    # from pyspark.sql.functions import udf
    # from pyspark.sql.types import ArrayType, StringType, StructField, StructType

    if text:
        if len(text) > MAXIMAL_STRING_SIZE:
            # Cut the strings for required sizes
            text = text[:MAXIMAL_STRING_SIZE]
        nlp = broadcasted_nlp.value
        doc = nlp(text)

        # Pre-create dictionary with labels matching to expected extracted entities
        classified_entities: dict[str, list[str]] = {
            _label: [] for _label in PII_ANNOTATION_LABELS
        }
        for ent in doc.ents:
            # Add entities from extracted values
            classified_entities[ent.label_].append(ent.text)

        return [_ent for _ent in classified_entities.values()]
    else:
        return [[] for _ in PII_ANNOTATION_LABELS]


def broadcast_pii_annotator_udf(
    spark_session=None, spacy_model: str = "en_core_web_lg"
):
    """Broadcast PII annotator across Spark cluster and create UDF"""
    # ensure_installed("pyspark")
    # ensure_installed("spacy")
    import spacy

    # from pyspark.sql import SparkSession
    # from pyspark.sql.functions import udf
    # from pyspark.sql.types import ArrayType, StringType, StructField, StructType

    if not spark_session:
        # spark_session = SparkSession.builder.getOrCreate()
        pass  # Placeholder if SparkSession is commented out

    # broadcasted_nlp = spark_session.sparkContext.broadcast(spacy.load(spacy_model))

    # pii_annotation_udf = udf(
    #     lambda text: pii_annotator(text, broadcasted_nlp),
    #     ArrayType(ArrayType(StringType())),
    # )
    return None  # Return None since the UDF creation is commented out


def ensure_installed(self, package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
