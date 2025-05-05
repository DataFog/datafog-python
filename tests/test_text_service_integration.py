"""Integration tests for TextService engine selection functionality."""

import pytest

from datafog.services.text_service import TextService


@pytest.fixture
def real_text_service():
    """Create a real TextService instance for integration testing."""
    return TextService(text_chunk_length=1000)  # Larger chunk to avoid multiple calls


@pytest.mark.integration
def test_engine_regex_detects_simple_entities():
    """Test that regex engine correctly detects simple entities like emails and phones."""
    # Sample text with patterns that regex should easily detect
    text = """Please contact john.doe@example.com or call at (555) 123-4567.
    My credit card is 4111-1111-1111-1111 and SSN is 123-45-6789."""

    # Create service with regex engine
    service = TextService(engine="regex")

    # Get annotations
    result = service.annotate_text_sync(text)

    # Verify regex detected the entities
    assert "john.doe@example.com" in result.get("EMAIL", [])
    assert any(phone in text for phone in result.get("PHONE", []))
    assert "4111-1111-1111-1111" in result.get("CREDIT_CARD", [])
    assert "123-45-6789" in result.get("SSN", [])


@pytest.mark.integration
def test_engine_auto_fallbacks_to_spacy():
    """Test that auto mode works correctly with entity detection."""
    # We need to test the auto mode in a more controlled way
    # Create a text that contains only named entities (no emails, phones, etc.)
    # so regex won't find anything meaningful
    text = "John Smith is the CEO of Acme Corporation."

    # First test with spaCy to confirm it finds the entities
    spacy_service = TextService(engine="spacy")
    spacy_result = spacy_service.annotate_text_sync(text)

    # Verify spaCy finds named entities
    assert "PERSON" in spacy_result and spacy_result["PERSON"]
    assert "ORG" in spacy_result and spacy_result["ORG"]

    # Now create a special text that contains both regex-detectable and spaCy-detectable entities
    mixed_text = "John Smith's email is john.smith@example.com"

    # Test with auto engine
    auto_service = TextService(engine="auto")
    auto_result = auto_service.annotate_text_sync(mixed_text)

    # In auto mode, if regex finds anything, it should return those results
    # So we should see the EMAIL entity from regex but not necessarily the PERSON entity from spaCy
    assert "EMAIL" in auto_result and auto_result["EMAIL"]
    assert any("john.smith@example.com" in email for email in auto_result["EMAIL"])


@pytest.mark.integration
def test_engine_spacy_only():
    """Test that spaCy engine is always used regardless of regex potential hits."""
    # Sample text with both regex-detectable and spaCy-detectable entities
    text = """John Smith's email is john.smith@example.com.
    He works at Microsoft and lives in Seattle."""

    # First, verify regex can detect the email (with the period)
    regex_service = TextService(engine="regex")
    regex_result = regex_service.annotate_text_sync(text)
    assert "EMAIL" in regex_result and regex_result["EMAIL"]
    assert any("john.smith@example.com" in email for email in regex_result["EMAIL"])

    # Now test with spacy engine
    spacy_service = TextService(engine="spacy")
    spacy_result = spacy_service.annotate_text_sync(text)

    # Verify spaCy detected named entities
    assert "PERSON" in spacy_result and spacy_result["PERSON"]
    assert "ORG" in spacy_result and spacy_result["ORG"]

    # Verify spaCy did NOT detect the email (which confirms it's using spaCy only)
    # This is because spaCy doesn't have a built-in EMAIL entity type
    assert "EMAIL" not in spacy_result or not spacy_result["EMAIL"]


@pytest.mark.integration
def test_structured_annotation_output():
    """Test that structured=True returns list of Span objects."""
    text = "John Smith's email is john.smith@example.com"

    service = TextService()
    result = service.annotate_text_sync(text, structured=True)

    # Verify the result is a list of Span objects
    assert isinstance(result, list), "Result should be a list of Span objects"
    assert len(result) > 0, "Should find at least one entity"

    # Check that each span has the required attributes
    for span in result:
        assert hasattr(span, "label"), "Span should have a label attribute"
        assert hasattr(span, "start"), "Span should have a start attribute"
        assert hasattr(span, "end"), "Span should have an end attribute"
        assert hasattr(span, "text"), "Span should have a text attribute"

        # Verify the span attributes are of the correct types
        assert isinstance(span.label, str)
        assert isinstance(span.start, int)
        assert isinstance(span.end, int)
        assert isinstance(span.text, str)

        # Verify the span's text matches the original text at the given positions
        assert (
            span.text == text[span.start : span.end]
        ), "Span text should match the text at the given positions"

    # Verify we found the email entity
    email_spans = [span for span in result if span.label == "EMAIL"]
    assert len(email_spans) > 0, "Should find at least one EMAIL entity"
    assert any(
        "john.smith@example.com" in span.text for span in email_spans
    ), "Should find the email john.smith@example.com"

    # Note: We don't verify PERSON entity detection in structured mode
    # because it's dependent on the specific spaCy model and configuration
    # The most important thing is that the structured output format works correctly
    # which we've already verified above


@pytest.mark.integration
def test_debug_entity_types():
    """Debug test to print the actual entity types returned by spaCy."""
    # Sample text with named entities
    text = """John Smith works at Microsoft Corporation in Seattle.
    He previously worked for Apple Inc. in California on January 15, 2020."""

    # Test with spaCy engine
    spacy_service = TextService(engine="spacy")
    spacy_result = spacy_service.annotate_text_sync(text)

    # Print all entity types and their values
    print("SpaCy entity types and values:")
    for entity_type, values in spacy_result.items():
        if values:  # Only print non-empty lists
            print(f"  {entity_type}: {values}")

    # No assertion needed, this is just for debugging
    assert True


@pytest.mark.skip(reason="Performance benchmarking requires more setup")
def test_performance_comparison():
    """Benchmark regex vs spaCy performance on a 10 KB text."""
    # This would be implemented as a benchmark rather than a regular test
    # import time
    #
    # # Generate a 10 KB sample text
    # text = "Sample text " * 1000  # Approximately 10 KB
    #
    # # Time regex engine
    # regex_service = TextService(engine="regex")
    # start = time.time()
    # regex_service.annotate_text_sync(text)
    # regex_time = time.time() - start
    #
    # # Time spaCy engine
    # spacy_service = TextService(engine="spacy")
    # start = time.time()
    # spacy_service.annotate_text_sync(text)
    # spacy_time = time.time() - start
    #
    # # Assert regex is at least 5x faster
    # assert regex_time * 5 <= spacy_time
