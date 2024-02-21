# datafog-python/src/datafog/pii_tools/presidio/__init__.py
from typing import List, Optional

import polars as pl
import requests
from posthog import Posthog
from presidio_analyzer import (
    AnalyzerEngine,
    BatchAnalyzerEngine,
    Pattern,
    PatternRecognizer,
)
from presidio_anonymizer import AnonymizerEngine, BatchAnonymizerEngine

posthog = Posthog(
    "phc_v6vMICyVCGoYZ2s2xUWB4qoTPoMNFGv2u1q0KnBpaIb", host="https://app.posthog.com"
)


def create_ad_hoc_deny_list_recognizer(
    deny_list: Optional[List[str]] = None,
) -> Optional[PatternRecognizer]:
    if not deny_list:
        return None

    deny_list_recognizer = PatternRecognizer(
        supported_entity="GENERIC_PII", deny_list=deny_list
    )
    return deny_list_recognizer


def create_ad_hoc_regex_recognizer(
    regex: str, entity_type: str, score: float, context: Optional[List[str]] = None
) -> Optional[PatternRecognizer]:
    if not regex:
        return None
    pattern = Pattern(name="Regex pattern", regex=regex, score=score)
    regex_recognizer = PatternRecognizer(
        supported_entity=entity_type, patterns=[pattern], context=context
    )
    return regex_recognizer


class PresidioEngine:

    def __init__(self, config=None):
        self.config = self.default_config() if config is None else config
        self.initialize_engine()
        # Simplify Posthog initialization (consider making analytics optional)

    @staticmethod  # TODO  need to make this a class method
    def default_config():
        """Return default configuration."""
        return {
            "nlp_engine": "spacy",
            "language": "en",
            # More default settings
        }

    def initialize_engine(self):
        # Initialize NLP and anonymizer engines based on configuration.
        # Logic to initialize based on self.config
        self.analyzer = AnalyzerEngine()
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.anonymizer = AnonymizerEngine()
        self.batch_anonymizer = BatchAnonymizerEngine()
        posthog.capture("device_id", "presidioengine_init")

    def process_input(
        self, input_data: str
    ) -> pl.DataFrame:  # TODO refactor because it is hacky
        """Process input data and return a DataFrame."""
        if input_data.startswith(("http://", "https://")) and not input_data.endswith(
            ".txt"
        ):
            response = requests.get(input_data)
            df = pl.read_csv(response.content)
        elif "\n" in input_data or "," in input_data or input_data.endswith(".csv"):
            df = pl.read_csv(input_data)
        else:
            df = pl.DataFrame(input_data)
        return df

    @staticmethod
    def analyze(
        model_family: str, model_path: str, ta_key: str, ta_endpoint: str, **kwargs
    ):
        """Analyze input using Analyzer engine and input arguments."""
        analyzer = PresidioEngine.analyzer_engine(
            model_family, model_path, ta_key, ta_endpoint
        )
        return analyzer.analyze(**kwargs)

    def anonymize(
        self,
        text: str,
        operator: str,
        analyze_results: dict,
        operator_config: dict,
    ):
        """Anonymize identified input using Presidio Anonymizer."""
        return self.anonymizer.anonymize(
            text=text,
            operator=operator,
            analyzer_results=analyze_results,
            **operator_config
        )

    @staticmethod
    def get_supported_entities(
        model_family: str, model_path: str, ta_key: str, ta_endpoint: str
    ) -> List[str]:
        """Return supported entities from the Analyzer Engine."""
        analyzer = PresidioEngine.analyzer_engine(
            model_family, model_path, ta_key, ta_endpoint
        )
        return analyzer.get_supported_entities() + ["GENERIC_PII"]
