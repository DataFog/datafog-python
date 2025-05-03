#!/bin/bash

# This script runs the benchmark tests locally and compares against a baseline
# It simulates the CI pipeline benchmark job without requiring GitHub Actions

set -e  # Exit on error

echo "=== Running benchmark tests locally ==="

# Create benchmarks directory if it doesn't exist
mkdir -p .benchmarks

# Run benchmarks and save results
echo "Running benchmarks and saving results..."
pytest tests/benchmark_text_service.py -v --benchmark-autosave

# Get the latest two benchmark runs
if [ -d ".benchmarks" ]; then
  # This assumes the benchmarks are stored in a platform-specific directory
  # Adjust the path if your pytest-benchmark uses a different structure
  BENCHMARK_DIR=$(find .benchmarks -type d -name "*-64bit" | head -n 1)
  
  if [ -n "$BENCHMARK_DIR" ] && [ -d "$BENCHMARK_DIR" ]; then
    RUNS=$(ls -t "$BENCHMARK_DIR" | head -n 2)
    NUM_RUNS=$(echo "$RUNS" | wc -l)
    
    if [ "$NUM_RUNS" -ge 2 ]; then
      BASELINE=$(echo "$RUNS" | tail -n 1)
      CURRENT=$(echo "$RUNS" | head -n 1)
      
      # Set full paths to the benchmark files
      BASELINE_FILE="$BENCHMARK_DIR/$BASELINE"
      CURRENT_FILE="$BENCHMARK_DIR/$CURRENT"
      
      echo "\nComparing current run ($CURRENT) against baseline ($BASELINE)"
      # First just show the comparison
      pytest tests/benchmark_text_service.py --benchmark-compare
      
      # Then check for significant regressions
      echo "\nChecking for performance regressions (>10% slower)..."
      # Use our Python script for benchmark comparison
      python scripts/compare_benchmarks.py "$BASELINE_FILE" "$CURRENT_FILE"
      
      if [ $? -eq 0 ]; then
        echo "\n✅ Performance is within acceptable range (< 10% regression)"
      else
        echo "\n❌ Performance regression detected! More than 10% slower than baseline."
      fi
    else
      echo "\nNot enough benchmark runs for comparison. Run this script again to create a comparison."
    fi
  else
    echo "\nBenchmark directory structure not found or empty."
  fi
else
  echo "\nNo benchmarks directory found. This is likely the first run."
fi

echo "\n=== Benchmark testing complete ==="
