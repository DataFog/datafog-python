import logging
from typing import List, Optional, Set, Tuple

from presidio_analyzer import AnalysisExplanation, LocalRecognizer, RecognizerResult

logger = logging.getLogger("custom-spacy-recognizer").setLevel(logging.ERROR)


class CustomSpacyRecognizer(LocalRecognizer):
    """
    Custom Spacy Recognizer for PII detection.

    This recognizer uses a pre-trained Spacy model to identify PII entities in text.

    Attributes:
        ENTITIES (List[str]): List of supported entities.
        DEFAULT_EXPLANATION (str): Default explanation format for recognized entities.
        CHECK_LABEL_GROUPS (List[Tuple[Set, Set]]): Groups of labels to check for entity matching.
        MODEL_LANGUAGES (Dict[str, str]): Mapping of language codes to pre-trained model names.
        PRESIDIO_EQUIVALENCES (Dict[str, str]): Mapping of Spacy entity labels to Presidio entity types.
    """

    ENTITIES = [
        "LOCATION",
        "PERSON",
        "NRP",
        "ORGANIZATION",
        "DATE_TIME",
    ]

    DEFAULT_EXPLANATION = "Identified as {} by the PII Detection Model"

    CHECK_LABEL_GROUPS = [
        ({"LOCATION"}, {"LOC", "LOCATION", "STREET_ADDRESS", "COORDINATE"}),
        ({"PERSON"}, {"PER", "PERSON"}),
        ({"NRP"}, {"NORP", "NRP"}),
        ({"ORGANIZATION"}, {"ORG"}),
        ({"DATE_TIME"}, {"DATE_TIME"}),
    ]

    MODEL_LANGUAGES = {
        "en": "beki/en_spacy_pii_fast",
    }

    PRESIDIO_EQUIVALENCES = {
        "PER": "PERSON",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        "NROP": "NRP",
        "DATE_TIME": "DATE_TIME",
    }

    def __init__(
        self,
        supported_language: str = "en",
        supported_entities: Optional[List[str]] = None,
        check_label_groups: Optional[Tuple[Set, Set]] = None,
        context: Optional[List[str]] = None,
        ner_strength: float = 0.85,
    ):
        """
        Initialize the CustomSpacyRecognizer.

        Args:
            supported_language (str): The language supported by the recognizer. Default is "en".
            supported_entities (Optional[List[str]]): List of supported entities. If None, defaults to ENTITIES.
            check_label_groups (Optional[Tuple[Set, Set]]): Groups of labels to check for entity matching.
                If None, defaults to CHECK_LABEL_GROUPS.
            context (Optional[List[str]]): Additional context for the recognizer. Default is None.
            ner_strength (float): The strength of the named entity recognition. Default is 0.85.
        """
        self.ner_strength = ner_strength
        self.check_label_groups = (
            check_label_groups if check_label_groups else self.CHECK_LABEL_GROUPS
        )
        supported_entities = supported_entities if supported_entities else self.ENTITIES
        super().__init__(
            supported_entities=supported_entities,
            supported_language=supported_language,
        )

    def load(self) -> None:
        """Load the model, not used. Model is loaded during initialization."""
        pass

    def get_supported_entities(self) -> List[str]:
        """
        Get the list of supported entities by the recognizer.

        Returns:
            List[str]: List of supported entities.
        """
        return self.supported_entities

    def build_spacy_explanation(
        self, original_score: float, explanation: str
    ) -> AnalysisExplanation:
        """
        Create explanation for why this result was detected.
        :param original_score: Score given by this recognizer
        :param explanation: Explanation string
        :return:
        """
        explanation = AnalysisExplanation(
            recognizer=self.__class__.__name__,
            original_score=original_score,
            textual_explanation=explanation,
        )
        return explanation

    def analyze(self, text, entities, nlp_artifacts=None):  # noqa D102
        """
        Analyze the given text for specified entities using the provided NLP artifacts.

        Args:
            text (str): The text to analyze.
            entities (List[str]): The list of entities to look for in the text.
            nlp_artifacts (Optional[NlpArtifacts]): The NLP artifacts to use for analysis. If None, an empty list is returned.

        Returns:
            List[RecognizerResult]: The list of recognized entities in the text.
        """
        results = []
        if not nlp_artifacts:
            logger.warning("No NLP artifacts provided for analysis")
            return results

        ner_entities = nlp_artifacts.entities

        for entity in entities:
            if entity not in self.supported_entities:
                continue
            for ent in ner_entities:
                if not self.__check_label(entity, ent.label_, self.check_label_groups):
                    continue
                textual_explanation = self.DEFAULT_EXPLANATION.format(ent.label_)
                explanation = self.build_spacy_explanation(
                    self.ner_strength, textual_explanation
                )

                spacy_result = RecognizerResult(
                    entity_type=entity,
                    start=ent.start_char,
                    end=ent.end_char,
                    score=self.ner_strength,
                    analysis_explanation=explanation,
                    recognition_metadata={
                        RecognizerResult.RECOGNIZER_NAME_KEY: self.name
                    },
                )

                results.append(spacy_result)

        return results

    @staticmethod
    def __check_label(
        entity: str, label: str, check_label_groups: Tuple[Set, Set]
    ) -> bool:
        """
        Check if the given entity and label belong to any of the specified label groups.

        Args:
            entity (str): The entity to check.
            label (str): The label to check.
            check_label_groups (Tuple[Set, Set]): The groups of labels to check against.

        Returns:
            bool: True if the entity and label belong to any of the label groups, False otherwise.
        """
        return any(
            [entity in egrp and label in lgrp for egrp, lgrp in check_label_groups]
        )
