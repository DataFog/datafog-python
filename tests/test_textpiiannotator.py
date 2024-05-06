import pytest

from datafog import PIIAnnotationModel, PIIAnnotationPipeline, PIIAnnotationRequest


@pytest.fixture
def pii_annotation_pipeline():
    model = PIIAnnotationModel()
    request = PIIAnnotationRequest(file_path="tests/test-invoice.png")
    return PIIAnnotationPipeline(request=request, model=model)


@pytest.fixture
def pii_annotation_model():
    model = PIIAnnotationModel()
    model.load_model()
    return model


def test_pii_annotation_model_loading(pii_annotation_model):
    # Ensure the model is loaded correctly
    assert (
        hasattr(pii_annotation_model, "nlp") and pii_annotation_model.nlp is not None
    ), "Model should be loaded"


def test_pii_annotation_request_validation():
    # Test with no fields filled
    with pytest.raises(ValueError):
        PIIAnnotationRequest().validate_fields()

    # Test with one field filled
    assert (
        PIIAnnotationRequest(text="Sample text").validate_fields() is True
    ), "Validation should pass when text is provided"


def test_pii_annotation_pipeline_processing(pii_annotation_pipeline):
    # Mock text processing
    pii_annotation_pipeline.request.text = "John Doe lives in Springfield."
    entities = pii_annotation_pipeline.process_request()
    assert len(entities) > 0, "Should detect entities"
    assert any("PER" in entity for entity in entities), "Should detect person entities"


def test_pii_annotation_pipeline_run(pii_annotation_pipeline):
    # Mock text for running the full pipeline
    pii_annotation_pipeline.request.text = "Jane Doe works at DataFog."
    response = pii_annotation_pipeline.run()
    assert (
        response.text == "Jane Doe works at DataFog."
    ), "Response text should match the request text"
    assert len(response.entities) > 0, "Should return detected entities"
    assert any(
        "ORG" in entity for entity in response.entities
    ), "Should detect organization entities"
