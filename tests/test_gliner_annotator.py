"""
Tests for GLiNER annotator integration.

Tests both the GLiNERAnnotator class directly and its integration with TextService.
Includes graceful degradation tests for when GLiNER dependencies are not available.
"""

from unittest.mock import Mock, patch

import pytest


class TestGLiNERAnnotatorWithDependencies:
    """Tests that require GLiNER dependencies to be installed."""

    @pytest.fixture
    def mock_gliner_model(self):
        """Mock GLiNER model for testing."""
        mock_model = Mock()
        mock_model.predict_entities.return_value = [
            {"label": "person", "text": "John Doe", "start": 0, "end": 8},
            {"label": "email", "text": "john@example.com", "start": 20, "end": 36},
            {"label": "phone number", "text": "555-123-4567", "start": 50, "end": 62},
        ]
        return mock_model

    @pytest.fixture
    def mock_gliner_class(self, mock_gliner_model):
        """Mock GLiNER class."""
        mock_class = Mock()
        mock_class.from_pretrained.return_value = mock_gliner_model
        return mock_class

    def test_gliner_annotator_creation_with_dependencies(self, mock_gliner_class):
        """Test GLiNER annotator creation when dependencies are available."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()

            assert annotator.model_name == "urchade/gliner_multi_pii-v1"
            assert "person" in annotator.entity_types
            assert "email" in annotator.entity_types
            mock_gliner_class.from_pretrained.assert_called_once_with(
                "urchade/gliner_multi_pii-v1"
            )

    def test_gliner_annotator_custom_model(self, mock_gliner_class):
        """Test GLiNER annotator with custom model."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            custom_entities = ["person", "organization", "location"]
            annotator = GLiNERAnnotator.create(
                model_name="urchade/gliner_base", entity_types=custom_entities
            )

            assert annotator.model_name == "urchade/gliner_base"
            assert annotator.entity_types == custom_entities
            mock_gliner_class.from_pretrained.assert_called_once_with(
                "urchade/gliner_base"
            )

    def test_gliner_annotate_text(self, mock_gliner_class, mock_gliner_model):
        """Test GLiNER text annotation."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()
            result = annotator.annotate(
                "John Doe works at john@example.com and his phone is 555-123-4567"
            )

            # Check that we got results for the detected entities
            assert "PERSON" in result
            assert "EMAIL" in result
            assert "PHONE_NUMBER" in result

            mock_gliner_model.predict_entities.assert_called_once()

    def test_gliner_annotate_empty_text(self, mock_gliner_class):
        """Test GLiNER annotation with empty text."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()
            result = annotator.annotate("")

            # Should return empty lists for all entity types
            assert all(
                isinstance(entities, list) and len(entities) == 0
                for entities in result.values()
            )

    def test_gliner_annotate_long_text(self, mock_gliner_class, mock_gliner_model):
        """Test GLiNER annotation with text exceeding max length."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()

            # Create text longer than MAXIMAL_STRING_SIZE
            long_text = "A" * 1000001  # Exceeds 1M character limit

            with patch(
                "datafog.processing.text_processing.gliner_annotator.logging"
            ) as mock_logging:
                result = annotator.annotate(long_text)

                # Should log a warning about truncation
                mock_logging.warning.assert_called_once()
                # Should still return a valid result
                assert isinstance(result, dict)

    def test_gliner_download_model(self, mock_gliner_class):
        """Test GLiNER model download functionality."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            GLiNERAnnotator.download_model("urchade/gliner_base")

            mock_gliner_class.from_pretrained.assert_called_once_with(
                "urchade/gliner_base"
            )

    def test_gliner_list_available_models(self):
        """Test listing available GLiNER models."""
        from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator

        models = GLiNERAnnotator.list_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "urchade/gliner_multi_pii-v1" in models
        assert "urchade/gliner_base" in models

    def test_gliner_get_model_info(self, mock_gliner_class):
        """Test getting model information."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()
            info = annotator.get_model_info()

            assert "model_name" in info
            assert "entity_types" in info
            assert "max_text_size" in info
            assert info["model_name"] == "urchade/gliner_multi_pii-v1"

    def test_gliner_set_entity_types(self, mock_gliner_class):
        """Test updating entity types."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            mock_gliner_class,
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            annotator = GLiNERAnnotator.create()
            new_entities = ["person", "location", "organization"]

            annotator.set_entity_types(new_entities)

            assert annotator.entity_types == new_entities


class TestGLiNERAnnotatorWithoutDependencies:
    """Tests for graceful degradation when GLiNER dependencies are not available."""

    def test_gliner_import_error_on_creation(self):
        """Test that ImportError is raised when GLiNER is not available."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            side_effect=ImportError(),
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            with pytest.raises(ImportError, match="GLiNER dependencies not available"):
                GLiNERAnnotator.create()

    def test_gliner_import_error_on_download(self):
        """Test that ImportError is raised when trying to download without GLiNER."""
        with patch(
            "datafog.processing.text_processing.gliner_annotator.GLiNER",
            side_effect=ImportError(),
        ):
            from datafog.processing.text_processing.gliner_annotator import (
                GLiNERAnnotator,
            )

            with pytest.raises(ImportError, match="GLiNER dependencies not available"):
                GLiNERAnnotator.download_model("urchade/gliner_base")


class TestTextServiceGLiNERIntegration:
    """Tests for GLiNER integration with TextService."""

    @pytest.fixture
    def mock_gliner_annotator(self):
        """Mock GLiNER annotator for TextService testing."""
        mock = Mock()
        mock.annotate.return_value = {
            "PERSON": ["John Doe"],
            "EMAIL": ["john@example.com"],
            "PHONE_NUMBER": [],
            "ORGANIZATION": [],
            "ADDRESS": [],
            "CREDIT_CARD_NUMBER": [],
            "SOCIAL_SECURITY_NUMBER": [],
            "DATE_OF_BIRTH": [],
            "MEDICAL_RECORD_NUMBER": [],
            "ACCOUNT_NUMBER": [],
            "LICENSE_NUMBER": [],
            "PASSPORT_NUMBER": [],
            "IP_ADDRESS": [],
            "URL": [],
            "LOCATION": [],
        }
        return mock

    def test_text_service_gliner_engine_init(self):
        """Test TextService initialization with GLiNER engine."""
        with patch("datafog.services.text_service.GLiNERAnnotator"):
            from datafog.services.text_service import TextService

            service = TextService(engine="gliner")
            assert service.engine == "gliner"
            assert service.gliner_model == "urchade/gliner_multi_pii-v1"

    def test_text_service_gliner_engine_custom_model(self):
        """Test TextService with custom GLiNER model."""
        with patch("datafog.services.text_service.GLiNERAnnotator"):
            from datafog.services.text_service import TextService

            service = TextService(engine="gliner", gliner_model="urchade/gliner_base")
            assert service.gliner_model == "urchade/gliner_base"

    def test_text_service_smart_engine_init(self):
        """Test TextService initialization with smart cascading engine."""
        with patch("datafog.services.text_service.GLiNERAnnotator"):
            from datafog.services.text_service import TextService

            service = TextService(engine="smart")
            assert service.engine == "smart"

    def test_text_service_gliner_engine_without_dependencies(self):
        """Test TextService GLiNER engine raises ImportError when dependencies missing."""
        with patch(
            "datafog.services.text_service.GLiNERAnnotator", side_effect=ImportError()
        ):
            from datafog.services.text_service import TextService

            with pytest.raises(
                ImportError, match="GLiNER engine requires additional dependencies"
            ):
                TextService(engine="gliner")

    def test_text_service_smart_engine_without_dependencies(self):
        """Test TextService smart engine raises ImportError when GLiNER dependencies missing."""
        with patch(
            "datafog.services.text_service.GLiNERAnnotator", side_effect=ImportError()
        ):
            from datafog.services.text_service import TextService

            with pytest.raises(
                ImportError, match="GLiNER engine requires additional dependencies"
            ):
                TextService(engine="smart")

    def test_text_service_valid_engines(self):
        """Test that all valid engines are accepted."""
        valid_engines = ["regex", "spacy", "gliner", "auto", "smart"]

        for engine in valid_engines:
            # Mock dependencies based on engine
            patches = []
            if engine in ["spacy", "auto"]:
                patches.append(patch("datafog.services.text_service.SpacyPIIAnnotator"))
            if engine in ["gliner", "smart"]:
                patches.append(patch("datafog.services.text_service.GLiNERAnnotator"))

            with patch.multiple(
                "datafog.services.text_service", **{p.attribute: p.new for p in patches}
            ):
                from datafog.services.text_service import TextService

                service = TextService(engine=engine)
                assert service.engine == engine

    def test_text_service_invalid_engine(self):
        """Test that invalid engines raise AssertionError."""
        from datafog.services.text_service import TextService

        with pytest.raises(AssertionError, match="Invalid engine"):
            TextService(engine="invalid_engine")

    @pytest.mark.parametrize(
        "engine,expected_count",
        [
            ("regex", 1),  # Stop after 1 entity
            ("gliner", 2),  # Stop after 2 entities
        ],
    )
    def test_cascade_should_stop_logic(self, engine, expected_count):
        """Test the cascade stopping logic."""
        from datafog.services.text_service import TextService

        service = TextService()

        # Test with exactly the threshold number of entities
        result_at_threshold = {"TYPE1": ["entity1"] * expected_count}
        assert service._cascade_should_stop(engine, result_at_threshold)

        # Test with one less than threshold
        if expected_count > 1:
            result_below_threshold = {"TYPE1": ["entity1"] * (expected_count - 1)}
            assert not service._cascade_should_stop(engine, result_below_threshold)

        # Test with more than threshold
        result_above_threshold = {"TYPE1": ["entity1"] * (expected_count + 1)}
        assert service._cascade_should_stop(engine, result_above_threshold)

    def test_smart_cascade_flow(self, mock_gliner_annotator):
        """Test the smart cascading flow."""
        with patch("datafog.services.text_service.RegexAnnotator") as mock_regex_cls:
            with patch(
                "datafog.services.text_service.GLiNERAnnotator"
            ) as mock_gliner_cls:
                with patch(
                    "datafog.services.text_service.SpacyPIIAnnotator"
                ) as mock_spacy_cls:

                    # Configure mocks
                    mock_regex = Mock()
                    mock_regex.annotate.return_value = {}  # No entities found
                    mock_regex_cls.return_value = mock_regex

                    mock_gliner_cls.create.return_value = mock_gliner_annotator

                    mock_spacy = Mock()
                    mock_spacy.annotate.return_value = {"PERSON": ["John Doe"]}
                    mock_spacy_cls.create.return_value = mock_spacy

                    from datafog.services.text_service import TextService

                    service = TextService(engine="smart")
                    service.annotate_text_sync("John Doe works at john@example.com")

                    # Should have tried regex first, then GLiNER
                    mock_regex.annotate.assert_called_once()
                    mock_gliner_annotator.annotate.assert_called_once()
