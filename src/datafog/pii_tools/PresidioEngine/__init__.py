from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .analyzer import CustomSpacyRecognizer


# Helper methods
def analyzer_engine():
    """Return AnalyzerEngine."""

    spacy_recognizer = CustomSpacyRecognizer()
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_spacy_pii_fast"}],
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
    # Set default values for any parameters not provided
    kwargs.setdefault("language", "en")
    kwargs.setdefault("score_threshold", 0.35)
    kwargs.setdefault("nlp_artifacts", None)

    # init analyzer instance
    analyzer = analyzer_engine()
    # Call the analyze method with the supported parameters
    return analyzer.analyze(text, **kwargs)
