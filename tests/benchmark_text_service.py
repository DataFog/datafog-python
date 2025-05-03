"""Benchmark tests for comparing regex vs spaCy performance in TextService."""

import time
from typing import Dict, List

import pytest

from datafog.processing.text_processing.regex_annotator import RegexAnnotator
from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator
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
    """Benchmark auto engine performance on a 10KB text."""
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
    print(f"\nAuto engine found entities: {entity_counts}")


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
    """Run a manual benchmark comparison between regex and spaCy."""
    # Generate sample text
    base_text = (
        "Contact John Doe at john.doe@example.com or call (555) 123-4567. "
        "His SSN is 123-45-6789 and credit card 4111-1111-1111-1111. "
        "He lives at 123 Main St, New York, NY 10001. "
        "His IP address is 192.168.1.1 and his birthday is 01/01/1980. "
        "Jane Smith works at Microsoft Corporation in Seattle, Washington. "
        "Her phone number is 555-987-6543 and email is jane.smith@company.org. "
    )

    # Repeat the text to reach approximately the desired size
    chars_per_kb = 1024
    target_size = text_size_kb * chars_per_kb
    repetitions = target_size // len(base_text) + 1
    sample_text = base_text * repetitions

    print(f"Generated sample text of {len(sample_text) / 1024:.2f} KB")

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

    # Benchmark auto
    start_time = time.time()
    auto_result = auto_service.annotate_text_sync(sample_text)
    auto_time = time.time() - start_time

    # Print results
    print(f"\nRegex time: {regex_time:.4f} seconds")
    print(f"SpaCy time: {spacy_time:.4f} seconds")
    print(f"Auto time: {auto_time:.4f} seconds")
    print(f"SpaCy is {spacy_time / regex_time:.2f}x slower than regex")

    # Print entity counts
    regex_counts = {key: len(values) for key, values in regex_result.items() if values}
    spacy_counts = {key: len(values) for key, values in spacy_result.items() if values}
    auto_counts = {key: len(values) for key, values in auto_result.items() if values}

    print(f"\nRegex found entities: {regex_counts}")
    print(f"SpaCy found entities: {spacy_counts}")
    print(f"Auto found entities: {auto_counts}")

    return {
        "regex_time": regex_time,
        "spacy_time": spacy_time,
        "auto_time": auto_time,
        "regex_counts": regex_counts,
        "spacy_counts": spacy_counts,
        "auto_counts": auto_counts,
    }


if __name__ == "__main__":
    # This allows running the manual benchmark directly
    # Example: python -m tests.benchmark_text_service
    results = manual_benchmark_comparison()
