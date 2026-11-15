"""Select a release version while refusing stale or already published bases."""

import argparse
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from packaging.version import Version


def select_version(
    current, release_type, tags, latest_stable, override=None, published=()
):
    if release_type not in {"alpha", "beta", "stable"}:
        raise ValueError("Unknown release type")
    source = Version(current)
    occupied = set(tags) | {f"v{Version(version)}" for version in published}
    base = override or source.base_version
    if not re.fullmatch(r"\d+\.\d+\.\d+", base):
        raise ValueError("Release base must be numeric major.minor.patch")
    if Version(base) <= Version(latest_stable):
        raise ValueError("Release base must be newer than the latest stable release")
    if release_type == "stable":
        candidate = base
    else:
        suffix = "a" if release_type == "alpha" else "b"
        number = 1
        while f"v{base}{suffix}{number}" in occupied:
            number += 1
        candidate = f"{base}{suffix}{number}"
    if f"v{candidate}" in occupied:
        raise ValueError(
            "Release tag already exists; inspect publication state before retrying"
        )
    return candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["alpha", "beta", "stable"])
    parser.add_argument("--override", default="")
    parser.add_argument(
        "--latest-stable", help="Offline preflight only; workflow reads PyPI"
    )
    args = parser.parse_args()
    tags = subprocess.check_output(["git", "tag", "-l"], text=True).splitlines()
    stable_tags = [tag[1:] for tag in tags if re.fullmatch(r"v\d+\.\d+\.\d+", tag)]
    if args.latest_stable:
        published = args.latest_stable
        published_versions = [published]
    else:
        with urllib.request.urlopen(
            "https://pypi.org/pypi/datafog/json", timeout=30
        ) as response:
            payload = json.load(response)
        releases = [
            Version(version)
            for version in payload["releases"]
            if not Version(version).is_prerelease
        ]
        published = str(max(releases))
        published_versions = list(payload["releases"])
    latest = str(max(Version(version) for version in [published, *stable_tags]))
    about = Path("datafog/__about__.py")
    current = re.search(r'^__version__ = "([^"]+)"', about.read_text(), re.M).group(1)
    candidate = select_version(
        current, args.type, tags, latest, args.override or None, published_versions
    )
    print(candidate)


if __name__ == "__main__":
    main()
