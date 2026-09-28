"""Reproduce the oracle from the exact published wheel in an isolated environment.

Writes a separate candidate file; never overwrites the committed contract.
"""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import runpy
import sys
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.isolated:
        parser.error("Use python -I to exclude the checkout and PYTHONPATH")
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "tests/contracts/4.8.1.json"
    if args.output.resolve() == fixture_path:
        parser.error("Capture to a separate candidate file for review")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    provenance = fixture["provenance"]
    digest = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    if digest != provenance["sha256"]:
        parser.error("Wheel does not match the frozen PyPI SHA-256")
    dist = importlib.metadata.distribution("datafog")
    if dist.version != "4.8.1":
        parser.error("Install the published 4.8.1 wheel first")
    # A version string alone cannot establish release provenance. Check installed
    # package bytes, then ensure imports resolve to that verified installation.
    with zipfile.ZipFile(args.wheel) as archive:
        for name in archive.namelist():
            if (
                name.startswith("datafog/")
                and not name.endswith("/")
                and Path(dist.locate_file(name)).read_bytes() != archive.read(name)
            ):
                parser.error(f"Installed file differs from published wheel: {name}")
    import datafog

    if (
        Path(datafog.__file__).resolve()
        != Path(dist.locate_file("datafog/__init__.py")).resolve()
    ):
        parser.error("datafog import is shadowed by another source tree")
    fixture["capture_environment"] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "pydantic",
                "pydantic-core",
                "pydantic-settings",
                "typing-extensions",
                "annotated-types",
                "python-dotenv",
                "typing-inspection",
            )
        },
    }
    runner = runpy.run_path(str(root / "tests/contract_481.py"))
    for case in fixture["cases"]:
        case["expected"] = runner["observe"](case)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    print(f"Captured {len(fixture['cases'])} cases to {args.output}")


if __name__ == "__main__":
    main()
