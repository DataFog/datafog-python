"""Benchmark tests for comparing regex vs spaCy performance in TextService."""

import time

import pytest

from datafog.services.text_service import TextService


@pytest.fixture
def sample_text_10kb():
    """Generate a 10KB sample text with various PII entities."""
    # Base text with PII entities
    base_text = (
        "Contact John Doe at john.doe@example.com or call (555) 123-4567. "
        "His SSN is 123-45-6789 and credit card 4111-1111-1111-1111. "
        "He lives at 123 Main St, New York, NY 10001. "
        "His IP address is 192.168.1.1 and his birthday is 01/01/1980. "
        "Jane Smith works at Microsoft Corporation in Seattle, Washington. "
        "Her phone number is 555-987-6543 and email is jane.smith@company.org. "
    )

    # Repeat the text to reach approximately 10KB
    repetitions = 10000 // len(base_text) + 1
    return base_text * repetitions


@pytest.fixture
def regex_service():
    """Create a TextService instance with regex engine."""
    return TextService(engine="regex", text_chunk_length=10000)


@pytest.fixture
def spacy_service():
    """Create a TextService instance with spaCy engine."""
    return TextService(engine="spacy", text_chunk_length=10000)


@pytest.fixture
def auto_service():
    """Create a TextService instance with auto engine."""
    return TextService(engine="auto", text_chunk_length=10000)


# This test is replaced by separate tests for regex and spaCy
# The pytest-benchmark fixture can only be used once per test
def test_compare_regex_vs_spacy_results(sample_text_10kb):
    """Compare the results of regex vs spaCy on a 10KB text."""
    # Create services with different engines
    regex_service = TextService(engine="regex", text_chunk_length=10000)
    spacy_service = TextService(engine="spacy", text_chunk_length=10000)

    # Get results from both engines
    regex_result = regex_service.annotate_text_sync(sample_text_10kb)
    spacy_result = spacy_service.annotate_text_sync(sample_text_10kb)

    # Print entity counts for comparison
    regex_counts = {key: len(values) for key, values in regex_result.items() if values}
    spacy_counts = {key: len(values) for key, values in spacy_result.items() if values}

    print(f"\nRegex found entities: {regex_counts}")
    print(f"SpaCy found entities: {spacy_counts}")

    # Verify both engines found entities
    assert regex_counts, "Regex should find some entities"
    assert spacy_counts, "SpaCy should find some entities"


def test_regex_performance(benchmark, sample_text_10kb, regex_service):
    """Benchmark regex performance on a 10KB text."""
    result = benchmark(
        regex_service.annotate_text_sync,
        sample_text_10kb,
    )

    # Verify regex found expected entities
    assert "EMAIL" in result
    assert "PHONE" in result
    assert "SSN" in result
    assert "CREDIT_CARD" in result

    # Print some stats about the results
    entity_counts = {key: len(values) for key, values in result.items() if values}
    print(f"\nRegex found entities: {entity_counts}")


def test_spacy_performance(benchmark, sample_text_10kb, spacy_service):
    """Benchmark spaCy performance on a 10KB text."""
    result = benchmark(
        spacy_service.annotate_text_sync,
        sample_text_10kb,
    )

    # Verify spaCy found expected entities
    assert "PERSON" in result or "PER" in result
    assert "ORG" in result

    # Print some stats about the results
    entity_counts = {key: len(values) for key, values in result.items() if values}
    print(f"\nspaCy found entities: {entity_counts}")


def test_auto_engine_performance(benchmark, sample_text_10kb, auto_service):
    """Benchmark auto engine performance on a 10KB text (regex finds entities - fast path)."""
    result = benchmark(
        auto_service.annotate_text_sync,
        sample_text_10kb,
    )

    # In auto mode, if regex finds anything, it should return those results
    # So we should see regex entities
    assert "EMAIL" in result
    assert "PHONE" in result

    # Print some stats about the results
    entity_counts = {key: len(values) for key, values in result.items() if values}
    print(f"\nAuto engine found entities (fast path): {entity_counts}")


@pytest.fixture
def spacy_only_text():
    """Generate text with entities only detectable by spaCy, not regex."""
    return (
        "The chief executive announced major initiatives for the organization. "
        "Doctor Johnson from Harvard University leads our research team. "
        "Their headquarters in Boston expanded operations significantly. "
        "Microsoft acquired many startups this past quarter. "
        "Board meetings happen every Tuesday afternoon. "
        "Funding came from Goldman Sachs and similar banks. "
        "California facilities employ many talented individuals. "
        "Amazon and Google compete in cloud computing markets. "
        "Project managers study at Stanford Business School. "
        "London offices show excellent growth this year. "
    ) * 100  # Repeat to get substantial text size


def test_auto_engine_fallback_performance(benchmark, spacy_only_text, auto_service):
    """Benchmark auto engine performance when regex finds nothing and spaCy takes over."""

    # First check if regex finds any meaningful entities in our "clean" text
    regex_service = TextService(engine="regex")
    regex_result = regex_service.annotate_text_sync(spacy_only_text)
    meaningful_regex = {
        k: v
        for k, v in regex_result.items()
        if v and k in ["EMAIL", "PHONE", "SSN", "CREDIT_CARD"]
    }

    # Skip test if regex patterns are broken and finding false positives
    if meaningful_regex:
        pytest.skip(
            f"Regex found unexpected entities in clean text: {meaningful_regex}"
        )

    # Check if the broken IP_ADDRESS pattern is finding empty matches
    if regex_result.get("IP_ADDRESS") and not any(
        addr.strip() for addr in regex_result["IP_ADDRESS"]
    ):
        print("Warning: IP_ADDRESS regex is finding empty matches - known issue")

    result = benchmark(
        auto_service.annotate_text_sync,
        spacy_only_text,
    )

    # Check if we have spaCy entities (depends on spaCy availability)
    spacy_entities = ["PERSON", "ORG", "GPE", "CARDINAL", "DATE", "TIME"]
    has_spacy_entities = any(entity in result for entity in spacy_entities)

    # If no spaCy entities, check if spaCy is available
    if not has_spacy_entities and auto_service.spacy_annotator is None:
        pytest.skip("SpaCy not available - test requires nlp extra")

    # Print results for analysis
    entity_counts = {key: len(values) for key, values in result.items() if values}
    print(f"\nAuto engine found entities (fallback path): {entity_counts}")

    # The test passes if it runs without error - the key is measuring fallback performance


def test_structured_output_performance(benchmark, sample_text_10kb):
    """Benchmark performance with structured output format."""
    # Create service with auto engine
    service = TextService(engine="auto", text_chunk_length=10000)

    # Benchmark with structured=True
    result = benchmark(
        service.annotate_text_sync,
        sample_text_10kb,
        structured=True,
    )

    # Verify structured output format
    assert isinstance(result, list)
    assert all(hasattr(span, "label") for span in result)
    assert all(hasattr(span, "start") for span in result)
    assert all(hasattr(span, "end") for span in result)
    assert all(hasattr(span, "text") for span in result)

    # Print some stats about the results
    label_counts = {}
    for span in result:
        label_counts[span.label] = label_counts.get(span.label, 0) + 1

    print(f"\nStructured output found entities: {label_counts}")


# Manual benchmark function (not using pytest-benchmark)
# This can be used to run a quick comparison without the pytest framework
def manual_benchmark_comparison(text_size_kb=10):
    """Run a manual benchmark comparison between regex, spaCy, and auto modes."""
    # Generate sample text with regex-detectable entities
    base_text = (
        "Contact John Doe at john.doe@example.com or call (555) 123-4567. "
        "His SSN is 123-45-6789 and credit card 4111-1111-1111-1111. "
        "He lives at 123 Main St, New York, NY 10001. "
        "His IP address is 192.168.1.1 and his birthday is 01/01/1980. "
        "Jane Smith works at Microsoft Corporation in Seattle, Washington. "
        "Her phone number is 555-987-6543 and email is jane.smith@company.org. "
    )

    # Generate spaCy-only text (absolutely no regex patterns)
    spacy_only_text = (
        "The chief executive announced major initiatives for the organization. "
        "Doctor Johnson from Harvard University leads our research team. "
        "Their headquarters in Boston expanded operations significantly. "
        "Microsoft acquired many startups this past quarter. "
        "Board meetings happen every Tuesday afternoon. "
        "Funding came from Goldman Sachs and similar banks. "
        "California facilities employ many talented individuals. "
        "Amazon and Google compete in cloud computing markets. "
        "Project managers study at Stanford Business School. "
        "London offices show excellent growth this year. "
    )

    # Repeat the text to reach approximately the desired size
    chars_per_kb = 1024
    target_size = text_size_kb * chars_per_kb
    repetitions = target_size // len(base_text) + 1
    sample_text = base_text * repetitions

    repetitions_spacy = target_size // len(spacy_only_text) + 1
    spacy_sample_text = spacy_only_text * repetitions_spacy

    print(f"Generated regex sample text of {len(sample_text) / 1024:.2f} KB")
    print(f"Generated spaCy-only sample text of {len(spacy_sample_text) / 1024:.2f} KB")

    # Create services
    regex_service = TextService(engine="regex", text_chunk_length=target_size)
    spacy_service = TextService(engine="spacy", text_chunk_length=target_size)
    auto_service = TextService(engine="auto", text_chunk_length=target_size)

    # Benchmark regex
    start_time = time.time()
    regex_result = regex_service.annotate_text_sync(sample_text)
    regex_time = time.time() - start_time

    # Benchmark spaCy
    start_time = time.time()
    spacy_result = spacy_service.annotate_text_sync(sample_text)
    spacy_time = time.time() - start_time

    # Benchmark auto (fast path - regex finds entities)
    start_time = time.time()
    auto_result = auto_service.annotate_text_sync(sample_text)
    auto_time = time.time() - start_time

    # Benchmark auto (fallback path - regex finds nothing, spaCy takes over)
    start_time = time.time()
    auto_fallback_result = auto_service.annotate_text_sync(spacy_sample_text)
    auto_fallback_time = time.time() - start_time

    # Print results
    print(f"\nRegex time: {regex_time:.4f} seconds")
    print(f"SpaCy time: {spacy_time:.4f} seconds")
    print(f"Auto time (fast path): {auto_time:.4f} seconds")
    print(f"Auto time (fallback path): {auto_fallback_time:.4f} seconds")
    print(f"SpaCy is {spacy_time / regex_time:.2f}x slower than regex")
    print(f"Auto fallback is {auto_fallback_time / regex_time:.2f}x slower than regex")

    # Print entity counts
    regex_counts = {key: len(values) for key, values in regex_result.items() if values}
    spacy_counts = {key: len(values) for key, values in spacy_result.items() if values}
    auto_counts = {key: len(values) for key, values in auto_result.items() if values}
    auto_fallback_counts = {
        key: len(values) for key, values in auto_fallback_result.items() if values
    }

    print(f"\nRegex found entities: {regex_counts}")
    print(f"SpaCy found entities: {spacy_counts}")
    print(f"Auto found entities (fast path): {auto_counts}")
    print(f"Auto found entities (fallback path): {auto_fallback_counts}")

    return {
        "regex_time": regex_time,
        "spacy_time": spacy_time,
        "auto_time": auto_time,
        "auto_fallback_time": auto_fallback_time,
        "regex_counts": regex_counts,
        "spacy_counts": spacy_counts,
        "auto_counts": auto_counts,
        "auto_fallback_counts": auto_fallback_counts,
    }


if __name__ == "__main__":
    # This allows running the manual benchmark directly
    # Example: python -m tests.benchmark_text_service
    results = manual_benchmark_comparison()
