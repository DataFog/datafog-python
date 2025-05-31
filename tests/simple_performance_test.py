#!/usr/bin/env python3
"""
Simple performance test that doesn't rely on pytest-benchmark plugin.
This can be used as a fallback if the benchmark plugin has issues in CI.
"""

import statistics
import time

from datafog.services.text_service import TextService


def generate_test_text():
    """Generate consistent test text for performance testing."""
    base_text = (
        "Contact John Doe at john.doe@example.com or call (555) 123-4567. "
        "His SSN is 123-45-6789 and credit card 4111-1111-1111-1111. "
        "He lives at 123 Main St, New York, NY 10001. "
        "His IP address is 192.168.1.1 and his birthday is 01/01/1980. "
        "Jane Smith works at Microsoft Corporation in Seattle, Washington. "
        "Her phone number is 555-987-6543 and email is jane.smith@company.org. "
    )
    # Use consistent moderate size (100 repetitions)
    return base_text * 100


def time_function(func, *args, **kwargs):
    """Time a function execution multiple times and return statistics."""
    times = []
    for _ in range(10):  # Run 10 times for more stable results
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "times": times,
        "result": result,
    }


def test_simple_regex_performance():
    """Simple regex performance test without pytest-benchmark dependency."""
    print("Testing regex performance...")

    text = generate_test_text()
    regex_service = TextService(engine="regex", text_chunk_length=10000)

    stats = time_function(regex_service.annotate_text_sync, text)

    print("Regex Performance:")
    print(f"  Mean: {stats['mean']:.2f}ms")
    print(f"  Median: {stats['median']:.2f}ms")
    print(f"  Min: {stats['min']:.2f}ms")
    print(f"  Max: {stats['max']:.2f}ms")
    print(f"  StdDev: {stats['stdev']:.2f}ms")

    # Verify functionality
    assert "EMAIL" in stats["result"]
    assert "PHONE" in stats["result"]
    assert "SSN" in stats["result"]

    # Performance sanity check (should be under 50ms for this text size)
    assert stats["mean"] < 50, f"Regex performance too slow: {stats['mean']:.2f}ms"

    return stats


def test_simple_spacy_performance():
    """Simple spaCy performance test without pytest-benchmark dependency."""
    print("Testing spaCy performance...")

    text = generate_test_text()

    try:
        spacy_service = TextService(engine="spacy", text_chunk_length=10000)
        stats = time_function(spacy_service.annotate_text_sync, text)

        print("SpaCy Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")
        print(f"  Min: {stats['min']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        print(f"  StdDev: {stats['stdev']:.2f}ms")

        # Verify functionality
        assert "PERSON" in stats["result"] or "PER" in stats["result"]
        assert "ORG" in stats["result"]

        return stats

    except ImportError:
        print("SpaCy not available - skipping spaCy performance test")
        return None


def run_simple_performance_comparison():
    """Run simple performance comparison and report results."""
    print("=" * 60)
    print("SIMPLE PERFORMANCE TEST (no pytest-benchmark)")
    print("=" * 60)

    regex_stats = test_simple_regex_performance()
    spacy_stats = test_simple_spacy_performance()

    if spacy_stats:
        speedup = spacy_stats["mean"] / regex_stats["mean"]
        print("\nPerformance Comparison:")
        print(f"  Regex: {regex_stats['mean']:.2f}ms")
        print(f"  SpaCy: {spacy_stats['mean']:.2f}ms")
        print(f"  Speedup: {speedup:.1f}x (regex vs spacy)")

        # Validate expected performance relationship
        assert (
            speedup > 5
        ), f"Regex should be at least 5x faster than spaCy, got {speedup:.1f}x"

    print("\n✅ Simple performance tests passed!")
    return {"regex": regex_stats, "spacy": spacy_stats}


if __name__ == "__main__":
    run_simple_performance_comparison()
