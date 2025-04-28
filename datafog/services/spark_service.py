"""
Spark service for data processing and analysis.

Provides a wrapper around PySpark functionality, including session creation,
JSON reading, and package management.
"""

import importlib
import json
import logging
import subprocess
import sys
from typing import Any, List, Optional

# Attempt to import pyspark and provide a helpful error message if missing
try:
    from pyspark.sql import DataFrame, SparkSession
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "pyspark is not installed. Please install it to use Spark features: pip install datafog[spark]"
    )

from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType


class SparkService:
    """
    Manages Spark operations and dependencies.

    Initializes a Spark session, handles imports, and provides methods for
    data reading and package installation.
    """

    def __init__(self):
        self.spark = self.create_spark_session()
        # self.ensure_installed("pyspark")

        # from pyspark.sql import DataFrame, SparkSession
        # from pyspark.sql.functions import udf
        # from pyspark.sql.types import ArrayType, StringType

        # self.SparkSession = SparkSession
        # self.DataFrame = DataFrame
        # self.udf = udf
        # self.ArrayType = ArrayType
        # self.StringType = StringType

        logging.info("SparkService initialized.")

    def create_spark_session(self):
        return SparkSession.builder.appName("datafog").getOrCreate()

    def read_json(self, path: str) -> List[dict]:
        return self.spark.read.json(path).collect()
