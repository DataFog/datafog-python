import logging
from typing import List, Optional

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .analyzer import CustomSpacyRecognizer

logger = logging.getLogger("presidio-engine-init").setLevel(logging.ERROR)


def create_ad_hoc_deny_list_recognizer(
    deny_list=Optional[List[str]],
) -> Optional[PatternRecognizer]:
    """
    Create an ad-hoc recognizer based on a provided deny list.

    Args:
        deny_list (Optional[List[str]]): List of terms to be denied. Default is None.

    Returns:
        Optional[PatternRecognizer]: A PatternRecognizer based on the provided deny list,
            or None if no deny list is provided.
    """
    if not deny_list:
        return None

    deny_list_recognizer = PatternRecognizer(
        supported_entity="CUSTOM_PII", deny_list=deny_list
    )
    return deny_list_recognizer


def create_ad_hoc_regex_recognizer(
    regex: str, entity_type: str, score: float, context: Optional[List[str]] = None
) -> Optional[PatternRecognizer]:
    """
    Create an ad-hoc recognizer based on a provided regular expression.

    Args:
        regex (str): The regular expression pattern to match.
        entity_type (str): The entity type associated with the pattern.
        score (float): The confidence score for the pattern.
        context (Optional[List[str]]): Additional context for the pattern. Default is None.

    Returns:
        Optional[PatternRecognizer]: A PatternRecognizer based on the provided regex,
            or None if no regex is provided.
    """
    if not regex:
        return None
    pattern = Pattern(name="Regex Pattern", regex=regex, score=score)
    regex_recognizer = PatternRecognizer(
        supported_entity=entity_type, patterns=[pattern], context=context
    )
    return regex_recognizer


def analyzer_engine():
    """
    Create and configure an AnalyzerEngine.

    Returns:
        AnalyzerEngine: The configured AnalyzerEngine instance.
    """

    spacy_recognizer = CustomSpacyRecognizer()
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_spacy_pii_fast"}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": {
                "PER": "PERSON",
                "PERSON": "PERSON",
                "NORP": "NRP",
                "FAC": "FACILITY",
                "LOC": "LOCATION",
                "GPE": "LOCATION",
                "LOCATION": "LOCATION",
                "ORG": "ORGANIZATION",
                "ORGANIZATION": "ORGANIZATION",
                "DATE": "DATE_TIME",
                "TIME": "DATE_TIME",
            },
            "low_confidence_score_multiplier": 0.4,
            "low_score_entity_names": ["ORG", "ORGANIZATION"],
            "labels_to_ignore": ["DATE_TIME", "NRP"],
        },
    }

    # Create NLP engine based on configuration
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry()

    # add rule-based recognizers
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)
    registry.add_recognizer(spacy_recognizer)

    # remove the nlp engine we passed, to use custom label mappings
    registry.remove_recognizer("SpacyRecognizer")

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine, registry=registry, supported_languages=["en"]
    )

    return analyzer


def annotate(text, analysis_results):
    """
    Annotate the input text with the analysis results.

    Args:
        text (str): The input text to annotate.
        analysis_results (List[AnalysisResult]): The list of analysis results.

    Returns:
        List[Union[str, Tuple[str, str]]]: The annotated text as a list of tokens,
            where each token is either a string or a tuple of (text, entity_type).
    """
    tokens = []
    # sort by start index
    results = sorted(analysis_results, key=lambda x: x.start)
    for i, res in enumerate(results):
        if i == 0:
            tokens.append(text[: res.start])

        # append entity text and entity type
        tokens.append((text[res.start : res.end], res.entity_type))

        # if another entity coming i.e. we're not at the last results element, add text up to next entity
        if i != len(results) - 1:
            tokens.append(text[res.end : results[i + 1].start])
        # if no more entities coming, add all remaining text
        else:
            tokens.append(text[res.end :])
    return tokens


def scan(text, **kwargs):
    """
    Analyze the input text using the Analyzer engine and provided arguments.

    Args:
        text (str): The input text to analyze.
        **kwargs: Additional keyword arguments for the analysis.
            - language (str): The language of the input text. Default is "en".
            - score_threshold (float): The minimum score threshold for entity recognition. Default is 0.35.
            - nlp_artifacts (Optional[NlpArtifacts]): NLP artifacts to use for analysis. Default is None.
            - entities (List[str]): List of entities to analyze. Default is an empty list.
            - allow_list (List[str]): List of terms to allow. Default is an empty list.
            - deny_list (List[str]): List of terms to deny. Default is an empty list.

    Returns:
        List[AnalysisResult]: The list of analysis results.
    """
    kwargs.setdefault("language", "en")
    kwargs.setdefault("score_threshold", 0.35)
    kwargs.setdefault("nlp_artifacts", None)
    kwargs.setdefault("entities", [])
    kwargs.setdefault("allow_list", [])
    kwargs.setdefault("deny_list", [])

    """Analyze input using Analyzer engine and input arguments (kwargs)."""
    if "entities" not in kwargs or "All" in kwargs["entities"]:
        kwargs["entities"] = None

    if "deny_list" in kwargs and kwargs["deny_list"] is not None:
        ad_hoc_recognizer = create_ad_hoc_deny_list_recognizer(kwargs["deny_list"])
        kwargs["ad_hoc_recognizers"] = [ad_hoc_recognizer] if ad_hoc_recognizer else []
        del kwargs["deny_list"]

    if "regex_params" in kwargs and len(kwargs["regex_params"]) > 0:
        ad_hoc_recognizer = create_ad_hoc_regex_recognizer(*kwargs["regex_params"])
        kwargs["ad_hoc_recognizers"] = [ad_hoc_recognizer] if ad_hoc_recognizer else []
        del kwargs["regex_params"]

    # init analyzer instance
    analyzer = analyzer_engine()
    # Call the analyze method with the supported parameters
    return analyzer.analyze(text, **kwargs)
