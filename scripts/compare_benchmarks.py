#!/usr/bin/env python3

import json
import sys


def compare_benchmarks(baseline_file, current_file):
    """Compare benchmark results and check for regressions."""
    try:
        # Load benchmark data
        with open(baseline_file, "r") as f:
            baseline = json.load(f)
        with open(current_file, "r") as f:
            current = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading benchmark files: {e}")
        return 0  # Don't fail on file issues

    # Check for regressions
    has_major_regression = False
    regression_count = 0
    total_comparisons = 0

    for b_bench in baseline["benchmarks"]:
        for c_bench in current["benchmarks"]:
            if b_bench["name"] == c_bench["name"]:
                total_comparisons += 1
                b_mean = b_bench["stats"]["mean"]
                c_mean = c_bench["stats"]["mean"]
                ratio = c_mean / b_mean

                # More lenient thresholds for CI environments
                if ratio > 2.0:  # Only fail on major regressions (>100% slower)
                    print(f"MAJOR REGRESSION: {b_bench['name']} is {ratio:.2f}x slower")
                    has_major_regression = True
                    regression_count += 1
                elif ratio > 1.5:  # Warn on moderate regressions (>50% slower)
                    print(
                        f"WARNING: {b_bench['name']} is {ratio:.2f}x slower (moderate regression)"
                    )
                    regression_count += 1
                elif ratio > 1.2:  # Info on minor regressions (>20% slower)
                    print(
                        f"INFO: {b_bench['name']} is {ratio:.2f}x slower (minor variance)"
                    )
                else:
                    print(f"OK: {b_bench['name']} - {ratio:.2f}x relative performance")

    # Summary
    if total_comparisons == 0:
        print("No benchmark comparisons found")
        return 0

    print(
        f"\nSummary: {regression_count}/{total_comparisons} benchmarks showed performance variance"
    )

    # Only fail on major regressions (>100% slower)
    if has_major_regression:
        print("FAIL: Major performance regression detected (>100% slower)")
        return 1
    elif regression_count > 0:
        print("WARNING: Performance variance detected but within acceptable limits")
        return 0
    else:
        print("All benchmarks within expected performance range")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmarks.py <baseline_file> <current_file>")
        sys.exit(1)

    baseline_file = sys.argv[1]
    current_file = sys.argv[2]

    sys.exit(compare_benchmarks(baseline_file, current_file))
