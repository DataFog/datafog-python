"""DataFog benchmark suite — reproduce every published performance number.

Usage::

    python benchmarks/run.py                      # all suites (skips missing deps)
    python benchmarks/run.py --suite core,hook    # subset
    python benchmarks/run.py --json results.json  # machine-readable output
    python benchmarks/run.py --quick              # fewer repeats, smaller payloads

Suites: core, guardrail, hook, spacy, presidio. See benchmarks/README.md
for methodology and how each number maps to the claims in the project
README and on datafog.ai.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _suites import SUITES, SuiteUnavailable  # noqa: E402
from _timing import Measurement  # noqa: E402


def _cpu_name() -> str:
    if sys.platform == "darwin":
        try:
            return subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return platform.processor() or platform.machine()


def _package_versions() -> dict[str, str]:
    versions = {}
    for package in ("datafog", "litellm", "presidio-analyzer", "spacy", "pydantic"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def environment() -> dict[str, object]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "cpu": _cpu_name(),
        "python": platform.python_version(),
        "packages": _package_versions(),
    }


def _fmt_value(value: float, unit: str) -> str:
    if unit == "us/op":
        if value >= 100_000:
            return f"{value / 1e6:8.2f} s"
        if value >= 1_000:
            return f"{value / 1e3:8.2f} ms"
        return f"{value:8.1f} µs"
    return f"{value:8.1f} ms"


def _fmt_meta(meta: dict[str, object]) -> str:
    parts = []
    for key in (
        "throughput_mb_s",
        "regex_speedup_x",
        "datafog_speedup_x",
        "p90",
        "detected",
        "note",
    ):
        if key in meta:
            value = meta[key]
            if key == "throughput_mb_s":
                parts.append(f"{value} MB/s")
            elif key.endswith("_speedup_x"):
                parts.append(f"{key.split('_speedup')[0]} is {value}x faster")
            elif key == "p90":
                parts.append(f"p90 {value:.1f} ms")
            else:
                parts.append(f"{key}: {value}")
    return "; ".join(str(p) for p in parts)


def print_report(results_by_suite: dict[str, list[Measurement]]) -> None:
    for suite, measurements in results_by_suite.items():
        print(f"\n## {suite}")
        width = max(len(m.name) for m in measurements)
        for m in measurements:
            spread = (
                f"±{_fmt_value(m.stdev, m.unit).strip():>10}"
                if m.repeats > 1
                else " " * 11
            )
            line = (
                f"  {m.name:<{width}}  median {_fmt_value(m.median, m.unit)} "
                f"{spread}  ({m.repeats}x{m.inner_loops} runs)"
            )
            extra = _fmt_meta(m.meta)
            print(line + (f"\n  {'':<{width}}    {extra}" if extra else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--suite",
        default="all",
        help=f"comma-separated subset of: {', '.join(SUITES)} (default: all)",
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="write results to a JSON file"
    )
    parser.add_argument(
        "--quick", action="store_true", help="fewer repeats, skip large payloads"
    )
    args = parser.parse_args()

    if args.suite == "all":
        selected = list(SUITES)
    else:
        selected = [s.strip() for s in args.suite.split(",") if s.strip()]
        unknown = [s for s in selected if s not in SUITES]
        if unknown:
            parser.error(
                f"unknown suite(s): {', '.join(unknown)}; choose from {', '.join(SUITES)}"
            )

    env = environment()
    print("DataFog benchmark suite")
    print(f"  {env['cpu']} | {env['platform']} | Python {env['python']}")
    print("  " + ", ".join(f"{k} {v}" for k, v in env["packages"].items()))

    results_by_suite: dict[str, list[Measurement]] = {}
    skipped: dict[str, str] = {}
    for suite in selected:
        print(f"\nrunning suite: {suite} ...", flush=True)
        try:
            results_by_suite[suite] = SUITES[suite](args.quick)
        except SuiteUnavailable as exc:
            skipped[suite] = str(exc)
            print(f"  skipped: {exc}")

    print_report(results_by_suite)
    if skipped:
        print("\nskipped suites:")
        for suite, reason in skipped.items():
            print(f"  {suite}: {reason}")

    if args.json:
        payload = {
            "environment": env,
            "results": [m.to_dict() for ms in results_by_suite.values() for m in ms],
            "skipped": skipped,
        }
        args.json.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"\nresults written to {args.json}")

    return 0 if results_by_suite else 1


if __name__ == "__main__":
    sys.exit(main())
