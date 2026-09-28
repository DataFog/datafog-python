"""Measure public Python/Rust bridge calls, including adaptation and cold startup."""

import argparse
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

os.environ["DATAFOG_NO_TELEMETRY"] = "1"

PAYLOADS = {
    "short": ("Contact alice@example.com", 200),
    "mixed": (
        "Email alice@example.com or call (555) 123-4567. "
        "SSN 123-45-6789; card 4111 1111 1111 1111; host 192.168.1.1.",
        100,
    ),
    "large_sparse": ("ordinary prose " * 70_000 + " alice@example.com", 3),
}


def measure(fn, text, backend, loops, samples):
    result = fn(text, backend=backend)
    durations = []
    for _ in range(samples):
        start = time.perf_counter()
        for _ in range(loops):
            fn(text, backend=backend)
        durations.append((time.perf_counter() - start) / loops * 1_000_000)
    return {
        "median_us": statistics.median(durations),
        "samples_us": durations,
        "entities": len(result.entities),
        "iterations_per_sample": loops,
    }


def cold_start(backend, samples):
    source = (
        "import datafog; "
        f"datafog.scan('Contact alice@example.com', backend={backend!r})"
    )
    durations = []
    for _ in range(samples):
        start = time.perf_counter()
        subprocess.run([sys.executable, "-c", source], check=True, capture_output=True)
        durations.append((time.perf_counter() - start) * 1_000)
    return {"median_ms": statistics.median(durations), "samples_ms": durations}


def main():
    import datafog

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be positive")
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "core_version": importlib.metadata.version("datafog-core"),
        "method": "One warmup call, median repeated calls; no ML. Cold = process+import+first scan.",
        "warm": [],
        "cold": {},
    }
    for name, (text, loops) in PAYLOADS.items():
        for operation in ("scan", "redact"):
            row = {
                "payload": name,
                "operation": operation,
                "utf8_bytes": len(text.encode()),
            }
            for backend in ("python", "rust"):
                row[backend] = measure(
                    getattr(datafog, operation), text, backend, loops, args.samples
                )
            report["warm"].append(row)
    for backend in ("python", "rust"):
        report["cold"][backend] = cold_start(backend, args.samples)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved end-to-end measurements to {args.output}")


if __name__ == "__main__":
    main()
