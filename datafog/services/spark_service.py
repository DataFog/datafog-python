import importlib
import json
import subprocess
import sys
from typing import Any, List


class SparkService:
    def __init__(self):
        self.spark = self.create_spark_session()
        self.ensure_installed("pyspark")

        from pyspark.sql import DataFrame, SparkSession
        from pyspark.sql.functions import udf
        from pyspark.sql.types import ArrayType, StringType

        self.SparkSession = SparkSession
        self.DataFrame = DataFrame
        self.udf = udf
        self.ArrayType = ArrayType
        self.StringType = StringType

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
