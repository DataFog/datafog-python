"""Compare applicable 4.8.1 observations with the opt-in Rust backend."""

import argparse
import copy
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

from tests.contract_481 import FIXTURE, observe

CORE_VERSION = importlib.metadata.version("datafog-core")
CORE_LINE = ".".join(CORE_VERSION.split(".")[:2])
DEVIATIONS = Path(__file__).parent / "contracts" / f"rust-{CORE_LINE}.0.json"
WRAPPER_DEVIATIONS = Path(__file__).parent / "contracts" / "wrapper-4.12.0.json"

TARGETS = {
    "datafog:scan",
    "datafog:redact",
    "datafog.engine:scan_and_redact",
    "datafog:sanitize",
    "datafog:scan_prompt",
    "datafog:filter_output",
}


def reviewed_deviation(case):
    """Layer explicit wrapper fixes on the unchanged historical wheel oracle."""
    wrapper = json.loads(WRAPPER_DEVIATIONS.read_text(encoding="utf-8"))
    native = json.loads(DEVIATIONS.read_text(encoding="utf-8"))
    return native["cases"].get(case["id"]) or wrapper["cases"].get(case["id"])


def expected_observation(case):
    deviation = reviewed_deviation(case)
    return copy.deepcopy(deviation["expected"] if deviation else case["expected"])


def applicable(case):
    return (
        case.get("operation", "call") == "call"
        and case.get("target") in TARGETS
        and "entities" not in case.get("kwargs", {})
    )


def native_observation(case):
    native_case = copy.deepcopy(case)
    native_case.setdefault("kwargs", {})["backend"] = "rust"
    return observe(native_case)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
    results = []
    for case in contract["cases"]:
        if not applicable(case):
            results.append({"id": case["id"], "status": "outside-backend-scope"})
            continue
        actual = native_observation(case)
        deviation = reviewed_deviation(case)
        expected = expected_observation(case)
        status = "regression" if actual != expected else "match"
        if status == "match" and deviation:
            status = deviation["classification"]
        results.append(
            {
                "id": case["id"],
                "status": status,
                "reason": deviation["reason"] if deviation else None,
                "legacy": case["expected"],
                "actual": actual,
            }
        )
    report = {
        "core_version": importlib.metadata.version("datafog-core"),
        "counts": dict(Counter(row["status"] for row in results)),
        "cases": results,
    }
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["counts"], sort_keys=True))
    return bool(report["counts"].get("regression"))


if __name__ == "__main__":
    raise SystemExit(main())
