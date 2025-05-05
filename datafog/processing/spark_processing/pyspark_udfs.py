"""
PySpark UDFs for PII annotation and related utilities.

This module provides functions for PII (Personally Identifiable Information) annotation
using SpaCy models in a PySpark environment. It includes utilities for installing
dependencies, creating and broadcasting PII annotator UDFs, and performing PII annotation
on text data.
"""

import importlib
import subprocess
import sys

PII_ANNOTATION_LABELS = ["DATE_TIME", "LOC", "NRP", "ORG", "PER"]
MAXIMAL_STRING_SIZE = 1000000


def pii_annotator(text: str, broadcasted_nlp) -> list[list[str]]:
    """Extract features using en_core_web_lg model.

    Returns:
        list[list[str]]: Values as arrays in order defined in the PII_ANNOTATION_LABELS.
    """
    ensure_installed("pyspark")
    ensure_installed("spacy")

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
    ensure_installed("pyspark")
    ensure_installed("spacy")
    import spacy
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf
    from pyspark.sql.types import ArrayType, StringType

    if not spark_session:
        spark_session = SparkSession.builder.getOrCreate()
    broadcasted_nlp = spark_session.sparkContext.broadcast(spacy.load(spacy_model))

    pii_annotation_udf = udf(
        lambda text: pii_annotator(text, broadcasted_nlp),
        ArrayType(ArrayType(StringType())),
    )
    return pii_annotation_udf


def ensure_installed(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
