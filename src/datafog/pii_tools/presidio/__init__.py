from typing import List, Optional

import polars as pl
import requests
from posthog import Posthog
from presidio_analyzer import (
    AnalyzerEngine,
    BatchAnalyzerEngine,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpEngine
from presidio_anonymizer import AnonymizerEngine, BatchAnonymizerEngine

from .nlp_engines import create_nlp_engine_with_spacy

posthog = Posthog(
    "phc_v6vMICyVCGoYZ2s2xUWB4qoTPoMNFGv2u1q0KnBpaIb", host="https://app.posthog.com"
)


class PresidioEngine:
    def __init__(
        self,
        registry: RecognizerRegistry = None,
        nlp_engine: NlpEngine = "spacy",
        log_decision_process: bool = False,
        default_score_threshold: float = 0.5,
        supported_languages: List[str] = ["en"],
    ):
        self.analyzer = AnalyzerEngine()
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.anonymizer = AnonymizerEngine()
        self.batch_anonymizer = BatchAnonymizerEngine()
        posthog.capture("device_id", "presidioengine_init")

    def process_input(self, input_data: str) -> pl.DataFrame:
        """Process input data and return a DataFrame."""
        if input_data.startswith(("http://", "https://")):
            response = requests.get(input_data)
            df = pl.read_csv(response.content)
        elif "\n" in input_data or "," in input_data or input_data.endswith(".csv"):
            df = pl.read_csv(input_data)
        else:
            df = pl.DataFrame(input_data)
        return df

    def __call__(self, input_data: str, language: str = "en") -> pl.DataFrame:
        df = self.process_input(input_data)
        posthog.capture(
            "device_id", "presidio_input_processed", properties={"num_rows": len(df)}
        )

        df_dict = {col: df[col].to_list() for col in df.columns}
        analyzer_results = self.batch_analyzer.analyze_dict(df_dict, language=language)
        anonymizer_results = self.batch_anonymizer.anonymize_dict(analyzer_results)
        scrubbed_df = pl.DataFrame(anonymizer_results)

        return scrubbed_df

    @staticmethod
    def analyzer_engine(
        model_family: str,
        model_path: str,
        ta_key: Optional[str] = None,
        ta_endpoint: Optional[str] = None,
    ) -> AnalyzerEngine:
        """Create and return an AnalyzerEngine instance."""
        nlp_engine, registry = create_nlp_engine_with_spacy(
            model_family, model_path, ta_key, ta_endpoint
        )
        return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)

    @staticmethod
    def anonymizer_engine() -> AnonymizerEngine:
        """Return AnonymizerEngine instance."""
        return AnonymizerEngine()

    @staticmethod
    def get_supported_entities(
        model_family: str, model_path: str, ta_key: str, ta_endpoint: str
    ) -> List[str]:
        """Return supported entities from the Analyzer Engine."""
        analyzer = PresidioEngine.analyzer_engine(
            model_family, model_path, ta_key, ta_endpoint
        )
        return analyzer.get_supported_entities() + ["GENERIC_PII"]

    @staticmethod
    def analyze(
        model_family: str, model_path: str, ta_key: str, ta_endpoint: str, **kwargs
    ):
        """Analyze input using Analyzer engine and input arguments."""
        analyzer = PresidioEngine.analyzer_engine(
            model_family, model_path, ta_key, ta_endpoint
        )
        return analyzer.analyze(**kwargs)

    @staticmethod
    def anonymize(
        text: str,
        operator: str,
        analyze_results: List[RecognizerResult],
        **operator_config
    ):
        """Anonymize identified input using Presidio Anonymizer."""
        anonymizer = PresidioEngine.anonymizer_engine()
        return anonymizer.anonymize(text, operator, analyze_results, **operator_config)
