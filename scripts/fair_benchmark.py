#!/usr/bin/env python3
"""
Fair Benchmark: Regex vs SpaCy PII Detection Performance

This script provides an unbiased comparison between regex-based and spaCy-based
PII detection in DataFog. It runs both engines on identical text data and
measures performance fairly.

The goal is to get accurate, defensible numbers for marketing claims.
"""

# Copy the minimal regex patterns and spaCy functionality we need
import re
import statistics
import time
from typing import Dict, List, Pattern, Tuple


class MinimalRegexAnnotator:
    """Minimal regex annotator for fair benchmarking."""

    def __init__(self):
        self.patterns: Dict[str, Pattern] = {
            "EMAIL": re.compile(
                r"[\w!#$%&'*+\-/=?^_`{|}~.]+@[\w\-.]+\.[\w\-.]+",
                re.IGNORECASE | re.MULTILINE,
            ),
            "PHONE": re.compile(
                r"(?:(?:\+|)1[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}",
                re.IGNORECASE | re.MULTILINE,
            ),
            "SSN": re.compile(
                r"\b(?!000|666)\d{3}-\d{2}-\d{4}\b", re.IGNORECASE | re.MULTILINE
            ),
            "CREDIT_CARD": re.compile(
                r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13})\b",
                re.IGNORECASE | re.MULTILINE,
            ),
            "IP_ADDRESS": re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                re.IGNORECASE | re.MULTILINE,
            ),
        }

    def annotate(self, text: str) -> Dict[str, List[str]]:
        """Find PII entities using regex patterns."""
        result = {label: [] for label in self.patterns.keys()}

        if not text:
            return result

        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                result[label].append(match.group())

        return result


class MinimalSpacyAnnotator:
    """Minimal spaCy annotator for fair benchmarking."""

    def __init__(self):
        import spacy

        # Use the small model for a fair comparison - it's what most users would have
        self.nlp = spacy.load("en_core_web_sm")

        # PII-relevant labels from spaCy
        self.pii_labels = [
            "PERSON",
            "ORG",
            "GPE",
            "CARDINAL",
            "DATE",
            "TIME",
            "MONEY",
            "PERCENT",
            "FAC",
            "LOC",
        ]

    def annotate(self, text: str) -> Dict[str, List[str]]:
        """Find PII entities using spaCy NLP."""
        result = {label: [] for label in self.pii_labels}

        if not text:
            return result

        # Limit text size to prevent memory issues
        if len(text) > 1000000:
            text = text[:1000000]

        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in result:
                result[ent.label_].append(ent.text)

        return result


def create_test_text() -> str:
    """Create a realistic test text with various PII entities."""

    # Base text with real-world PII patterns
    base_text = """
    Dear John Smith,

    Thank you for your interest in our services. Please confirm your details:

    Email: john.smith@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Credit Card: 4532 1234 5678 9012
    Address: 123 Main Street, New York, NY 10001
    IP Address: 192.168.1.1
    Date of Birth: 03/15/1985

    We also have records for the following contacts:
    - Sarah Johnson (sarah.j@company.org) - Phone: 555.987.6543
    - Michael Brown (m.brown@corporation.net) - SSN: 987-65-4321
    - Amazon Inc. located in Seattle, WA
    - Meeting scheduled for January 15th, 2024 at 2:30 PM
    - Payment of $1,500.00 processed on 12/01/2023
    - Server IP: 10.0.0.1, Database IP: 172.16.0.1

    Additional test cases:
    - Credit cards: 5555555555554444, 378282246310005
    - Phone variations: +1-800-555-0199, 1.800.555.0123, (800) 555-0156
    - Email variants: test.email+tag@domain.co.uk, user_name@sub.domain.org
    - Organizations: Microsoft Corporation, Google LLC, Apple Inc.
    - Locations: San Francisco, California; London, England; Tokyo, Japan
    - People: Elizabeth Warren, Barack Obama, Taylor Swift
    - Dates: February 29, 2020; 2023-12-31; 01/01/2000
    - Times: 9:30 AM, 14:45, 11:59 PM
    - Money: $50.00, €100.50, £75.25, $1,000,000
    - Percentages: 25%, 99.9%, 0.1%

    End of test document.
    """

    return base_text.strip()


def benchmark_engine(
    annotator, text: str, engine_name: str, num_runs: int = 5
) -> Tuple[float, Dict]:
    """Benchmark a single engine multiple times."""
    times = []
    results = None

    print(f"\nBenchmarking {engine_name}...")

    # Warmup run (not counted)
    _ = annotator.annotate(text)

    # Measured runs
    for i in range(num_runs):
        start_time = time.perf_counter()
        results = annotator.annotate(text)
        end_time = time.perf_counter()

        run_time = end_time - start_time
        times.append(run_time)
        print(f"  Run {i + 1}: {run_time * 1000:.2f} ms")

    avg_time = statistics.mean(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0

    print(f"  Average: {avg_time * 1000:.2f} ms ± {std_dev * 1000:.2f} ms")

    return avg_time, results


def analyze_results(regex_results: Dict, spacy_results: Dict):
    """Analyze what each engine found."""

    print("\n" + "=" * 60)
    print("ENTITY DETECTION ANALYSIS")
    print("=" * 60)

    print("\nRegex Engine Results:")
    regex_total = 0
    for label, entities in regex_results.items():
        if entities:
            print(f"  {label}: {len(entities)} entities")
            # Show first few examples
            examples = entities[:3]
            if len(entities) > 3:
                examples.append(f"... (+{len(entities) - 3} more)")
            print(f"    Examples: {examples}")
            regex_total += len(entities)
    print(f"  TOTAL: {regex_total} entities")

    print("\nSpaCy Engine Results:")
    spacy_total = 0
    for label, entities in spacy_results.items():
        if entities:
            print(f"  {label}: {len(entities)} entities")
            # Show first few examples
            examples = entities[:3]
            if len(entities) > 3:
                examples.append(f"... (+{len(entities) - 3} more)")
            print(f"    Examples: {examples}")
            spacy_total += len(entities)
    print(f"  TOTAL: {spacy_total} entities")


def main():
    """Run the fair benchmark comparison."""

    print("DataFog Fair Benchmark: Regex vs SpaCy PII Detection")
    print("=" * 60)

    # Create test text
    test_text = create_test_text()
    text_size_kb = len(test_text.encode("utf-8")) / 1024

    print(f"Test text size: {text_size_kb:.2f} KB")
    print(f"Test text length: {len(test_text):,} characters")

    # Scale up the text to get more reliable measurements
    # Repeat the text multiple times to create a larger sample
    multiplier = 10  # This gives us ~50KB of text
    scaled_text = test_text * multiplier
    scaled_size_kb = len(scaled_text.encode("utf-8")) / 1024

    print(f"Scaled text size: {scaled_size_kb:.2f} KB ({multiplier}x multiplier)")

    # Initialize engines
    print("\nInitializing engines...")
    regex_annotator = MinimalRegexAnnotator()
    spacy_annotator = MinimalSpacyAnnotator()

    # Benchmark both engines
    num_runs = 5

    regex_time, regex_results = benchmark_engine(
        regex_annotator, scaled_text, "Regex Engine", num_runs
    )

    spacy_time, spacy_results = benchmark_engine(
        spacy_annotator, scaled_text, "SpaCy Engine", num_runs
    )

    # Calculate performance metrics
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)

    speedup_ratio = spacy_time / regex_time
    regex_throughput = scaled_size_kb / regex_time
    spacy_throughput = scaled_size_kb / spacy_time

    print("\nRegex Engine:")
    print(f"  Average time: {regex_time * 1000:.2f} ms")
    print(f"  Throughput: {regex_throughput:,.0f} KB/s")

    print("\nSpaCy Engine:")
    print(f"  Average time: {spacy_time * 1000:.2f} ms")
    print(f"  Throughput: {spacy_throughput:,.0f} KB/s")

    print("\nPerformance Ratio:")
    print(f"  Regex is {speedup_ratio:.1f}x faster than SpaCy")
    print(f"  SpaCy takes {spacy_time / regex_time:.1f}x longer than Regex")

    # Analyze entity detection
    analyze_results(regex_results, spacy_results)

    # Summary for marketing
    print("\n" + "=" * 60)
    print("MARKETING SUMMARY")
    print("=" * 60)
    print(f"✅ Regex is {speedup_ratio:.1f}x faster than SpaCy")
    print(f"✅ Regex throughput: {regex_throughput:,.0f} KB/s")
    print(f"✅ SpaCy throughput: {spacy_throughput:,.0f} KB/s")
    print(f"✅ Test completed successfully on {scaled_size_kb:.1f} KB of text")


if __name__ == "__main__":
    main()
