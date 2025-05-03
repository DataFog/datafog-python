"""
Spark service for data processing and analysis.

Provides a wrapper around PySpark functionality, including session creation,
JSON reading, and package management.
"""

import importlib
import json
import subprocess
import sys
from typing import Any, List


class SparkService:
    """
    Manages Spark operations and dependencies.

    Initializes a Spark session, handles imports, and provides methods for
    data reading and package installation.
    """

    def __init__(self):
        # First import necessary modules
        from pyspark.sql import DataFrame, SparkSession
        from pyspark.sql.functions import udf
        from pyspark.sql.types import ArrayType, StringType

        # Assign fields
        self.SparkSession = SparkSession
        self.DataFrame = DataFrame
        self.udf = udf
        self.ArrayType = ArrayType
        self.StringType = StringType

        # Now create spark session and ensure pyspark is installed
        self.ensure_installed("pyspark")
        self.spark = self.create_spark_session()

    def create_spark_session(self):
        return self.SparkSession.builder.appName("datafog").getOrCreate()

    def read_json(self, path: str) -> List[dict]:
        return self.spark.read.json(path).collect()

    def ensure_installed(self, package_name):
        try:
            importlib.import_module(package_name)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name]
            )
