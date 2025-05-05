"""
Spark service for data processing and analysis.

Provides a wrapper around PySpark functionality, including session creation,
JSON reading, and package management.
"""

import importlib
import os
import subprocess
import sys
from typing import List


class SparkService:
    """
    Manages Spark operations and dependencies.

    Initializes a Spark session, handles imports, and provides methods for
    data reading and package installation.
    """

    def __init__(self, master=None):
        self.master = master

        # Ensure pyspark is installed first
        self.ensure_installed("pyspark")

        # Now import necessary modules after ensuring pyspark is installed
        try:
            from pyspark.sql import DataFrame, SparkSession
            from pyspark.sql.functions import udf
            from pyspark.sql.types import ArrayType, StringType

            # Assign fields
            self.SparkSession = SparkSession
            self.DataFrame = DataFrame
            self.udf = udf
            self.ArrayType = ArrayType
            self.StringType = StringType

            # Create the spark session
            self.spark = self.create_spark_session()
        except ImportError as e:
            raise ImportError(
                f"Failed to import PySpark modules: {e}. "
                f"Make sure PySpark is installed correctly."
            )

    def create_spark_session(self):
        # Check if we're running in a test environment
        in_test_env = (
            "PYTEST_CURRENT_TEST" in os.environ or "TOX_ENV_NAME" in os.environ
        )

        # Set Java system properties to handle security manager issues
        # This is needed for newer Java versions
        os.environ["PYSPARK_SUBMIT_ARGS"] = (
            "--conf spark.driver.allowMultipleContexts=true pyspark-shell"
        )

        # Create a builder with the app name
        builder = self.SparkSession.builder.appName("datafog")

        # Add configuration to work around security manager issues
        builder = builder.config("spark.driver.allowMultipleContexts", "true")
        builder = builder.config(
            "spark.driver.extraJavaOptions", "-Djava.security.manager=allow"
        )

        # If master is specified, use it
        if self.master:
            builder = builder.master(self.master)
        # Otherwise, if we're in a test environment, use local mode
        elif in_test_env:
            builder = builder.master("local[1]")

        # Create and return the session
        return builder.getOrCreate()

    def read_json(self, path: str) -> List[dict]:
        return self.spark.read.json(path).collect()

    def ensure_installed(self, package_name):
        try:
            importlib.import_module(package_name)
        except ImportError:
            print(f"Installing {package_name}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package_name]
                )
                print(f"{package_name} installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package_name}: {e}")
                raise ImportError(
                    f"Could not install {package_name}. "
                    f"Please install it manually with 'pip install {package_name}'."
                )
