# from .pyspark_udfs import broadcast_pii_annotator_udf, pii_annotator


def get_pyspark_udfs():
    from .pyspark_udfs import broadcast_pii_annotator_udf, pii_annotator

    return broadcast_pii_annotator_udf, pii_annotator
