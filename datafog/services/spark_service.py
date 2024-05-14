import json
from typing import Any, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType


class SparkService:
    def __init__(self):
        self.spark = self.create_spark_session()

    @staticmethod
    def create_spark_session() -> SparkSession:
        """Create and configure a Spark session."""
        return (
            SparkSession.builder.appName("DataFog")
            .config("spark.driver.memory", "8g")
            .config("spark.executor.memory", "8g")
            .getOrCreate()
        )

    def create_dataframe(self, data: List[tuple], schema: List[str]) -> DataFrame:
        """Convert a list of tuples to a Spark DataFrame with the specified schema."""
        return self.spark.createDataFrame(data, schema)

    def add_pii_annotations(self, df: DataFrame, annotation_udf: udf) -> DataFrame:
        """Add a new column to DataFrame with PII annotations."""
        return df.withColumn("pii_annotations", annotation_udf(df["text"]))

    def write_to_json(self, data: Any, output_path: str):
        """Write data to a JSON file."""
        with open(output_path, "w") as f:
            json.dump(data, f)

    def stop(self):
        """Stop the Spark session."""
        self.spark.stop()
