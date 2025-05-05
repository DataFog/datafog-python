#!/usr/bin/env python3

import json
import sys


def compare_benchmarks(baseline_file, current_file):
    """Compare benchmark results and check for regressions."""
    # Load benchmark data
    with open(baseline_file, "r") as f:
        baseline = json.load(f)
    with open(current_file, "r") as f:
        current = json.load(f)

    # Check for regressions
    has_regression = False
    for b_bench in baseline["benchmarks"]:
        for c_bench in current["benchmarks"]:
            if b_bench["name"] == c_bench["name"]:
                b_mean = b_bench["stats"]["mean"]
                c_mean = c_bench["stats"]["mean"]
                ratio = c_mean / b_mean
                if ratio > 1.1:  # 10% regression threshold
                    print(f"REGRESSION: {b_bench['name']} is {ratio:.2f}x slower")
                    has_regression = True
                else:
                    print(f"OK: {b_bench['name']} - {ratio:.2f}x relative performance")

    # Exit with error if regression found
    return 1 if has_regression else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmarks.py <baseline_file> <current_file>")
        sys.exit(1)

    baseline_file = sys.argv[1]
    current_file = sys.argv[2]

    sys.exit(compare_benchmarks(baseline_file, current_file))
