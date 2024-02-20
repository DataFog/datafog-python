import polars as pl
from posthog import Posthog
from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, BatchAnonymizerEngine

posthog = Posthog(
    "phc_v6vMICyVCGoYZ2s2xUWB4qoTPoMNFGv2u1q0KnBpaIb", host="https://app.posthog.com"
)


class PresidioPolarFog:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.anonymizer = AnonymizerEngine()
        self.batch_anonymizer = BatchAnonymizerEngine()
        posthog.capture("device_id", "presidiopolarfog_init")

    def __call__(self, file_path: str) -> None:
        # Convert file to dataframe
        df = pl.read_csv(file_path)
        posthog.capture(
            "device_id", "presidiopolarfog_read_csv", properties={"num_rows": len(df)}
        )
        posthog.capture(
            "device_id",
            "presidiopolarfog_read_csv",
            properties={"num_columns": len(df.columns)},
        )

        # Scrub the dataframe
        df_dict = {col: df[col].to_list() for col in df.columns}

        analyzer_results = self.batch_analyzer.analyze_dict(df_dict, language="en")
        analyzer_results = list(analyzer_results)
        anonymizer_results = self.batch_anonymizer.anonymize_dict(analyzer_results)
        scrubbed_df = pl.DataFrame(anonymizer_results)

        # Write the scrubbed dataframe to a file with "_scanned" appended to the filename
        output_file_path = (
            file_path.rsplit(".", 1)[0] + "_scanned." + file_path.rsplit(".", 1)[1]
        )
        scrubbed_df.write_csv(output_file_path)
