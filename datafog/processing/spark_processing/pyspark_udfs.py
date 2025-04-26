"""
PySpark UDFs for PII annotation and related utilities.

This module provides functions for PII (Personally Identifiable Information) annotation
using SpaCy models in a PySpark environment. It includes utilities for installing
dependencies, creating and broadcasting PII annotator UDFs, and performing PII annotation
on text data.
"""

import logging
import sys
import importlib
import subprocess

# Attempt imports and provide helpful error messages
try:
    from pyspark.sql.functions import udf
    from pyspark.sql.types import StringType, ArrayType
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "pyspark is not installed. Please install it to use Spark features: pip install datafog[spark]"
    )

try:
    import spacy
except ModuleNotFoundError:
    # Spacy is a core dependency, but let's provide a helpful message just in case.
    raise ModuleNotFoundError(
        "spacy is not installed. Please ensure datafog is installed correctly: pip install datafog"
    )


from typing import List

PII_ANNOTATION_LABELS = ["DATE_TIME", "LOC", "NRP", "ORG", "PER"]
MAXIMAL_STRING_SIZE = 1000000


def pii_annotator(text: str, broadcasted_nlp) -> List[List[str]]:
    """Extract features using en_core_web_lg model.

    Returns:
        list[list[str]]: Values as arrays in order defined in the PII_ANNOTATION_LABELS.
    """
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
    if not spark_session:
        spark_session = SparkSession.builder.getOrCreate()
    broadcasted_nlp = spark_session.sparkContext.broadcast(spacy.load(spacy_model))

    pii_annotation_udf = udf(
        lambda text: pii_annotator(text, broadcasted_nlp),
        ArrayType(ArrayType(StringType())),
    )
    return pii_annotation_udf
