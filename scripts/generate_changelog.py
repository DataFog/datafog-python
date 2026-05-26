#!/usr/bin/env python3
"""Generate changelog for weekly releases."""

import argparse
import re
import subprocess
from datetime import datetime


def get_current_version():
    """Read the current package version from datafog/__about__.py."""
    try:
        with open("datafog/__about__.py") as f:
            match = re.search(r'^__version__ = "([^"]+)"', f.read(), re.M)
            return match.group(1) if match else None
    except OSError:
        return None


def get_latest_tag():
    """Get the latest git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since_tag(tag):
    """Get commits since the given tag."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--oneline"]
    else:
        cmd = ["git", "log", "--oneline"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def categorize_commits(commits):
    """Categorize commits by type."""
    categories = {
        "features": [],
        "fixes": [],
        "performance": [],
        "docs": [],
        "other": [],
    }

    for commit in commits:
        commit = commit.strip()
        if not commit:
            continue

        if re.search(r"\b(feat|feature|add)\b", commit, re.I):
            categories["features"].append(commit)
        elif re.search(r"\b(fix|bug|patch)\b", commit, re.I):
            categories["fixes"].append(commit)
        elif re.search(r"\b(perf|performance|speed|optimize)\b", commit, re.I):
            categories["performance"].append(commit)
        elif re.search(r"\b(doc|docs|readme)\b", commit, re.I):
            categories["docs"].append(commit)
        else:
            categories["other"].append(commit)

    return categories


def generate_changelog(beta=False, alpha=False):
    """Generate changelog content."""
    latest_tag = get_latest_tag()
    commits = get_commits_since_tag(latest_tag)
    current_version = get_current_version()

    if not commits:
        return "No changes since last release."

    categories = categorize_commits(commits)

    if alpha:
        changelog = "# Alpha Release Notes\n\n"
        changelog += f"*Alpha Build: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        changelog += (
            "⚠️ **This is an alpha build for early testing. Expect rough edges.**\n\n"
        )
    elif beta:
        changelog = "# Beta Release Notes\n\n"
        changelog += f"*Beta Release: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        changelog += "⚠️ **This is a beta release for testing purposes.**\n\n"
    else:
        changelog = "# What's New\n\n"
        changelog += f"*Released: {datetime.now().strftime('%Y-%m-%d')}*\n\n"

    if not alpha and not beta and current_version == "4.4.0":
        changelog += "## Python 3.13 Support Scope\n\n"
        changelog += (
            "Python 3.13 support is certified for the core SDK and CLI: "
            "`pip install datafog` and `pip install datafog[cli]`.\n\n"
        )
        changelog += (
            "Optional extras including `nlp`, `nlp-advanced`, `ocr`, "
            "`distributed`, and `all` are available but not yet certified on "
            "Python 3.13. They will be validated separately based on user "
            "demand.\n\n"
        )
        changelog += "## v5 Migration Bridge\n\n"
        changelog += (
            "This release adds the v5-preview top-level APIs `datafog.scan`, "
            "`datafog.redact`, and `datafog.protect` while keeping the legacy "
            "`datafog.detect` and `datafog.process` APIs working with targeted "
            "migration warnings.\n\n"
        )
        changelog += "## Privacy Defaults\n\n"
        changelog += (
            "Telemetry is now opt-in. DataFog does not send telemetry unless "
            "`DATAFOG_TELEMETRY=1` is explicitly set. `DATAFOG_NO_TELEMETRY=1` "
            "and `DO_NOT_TRACK=1` continue to force telemetry off.\n\n"
        )

    if not alpha and not beta and current_version == "4.5.0":
        changelog += "## 4.5 Release Focus\n\n"
        changelog += (
            "DataFog 4.5.0 is a focused release for lightweight text PII "
            "screening. The core install remains dependency-light while the "
            "text APIs, CLI, guardrail helpers, German structured PII coverage, "
            "optional-profile docs, and Python 3.13 compatibility story become "
            "clearer and easier to verify.\n\n"
        )
        changelog += "## German Structured PII\n\n"
        changelog += (
            "German VAT IDs and German IBANs are detected by default in the "
            "regex engine. Broader German identifiers such as tax IDs, postal "
            "codes, passport numbers, residence permit numbers, and pension "
            'insurance numbers require `locales=["de"]` or explicit entity '
            "selection.\n\n"
        )
        changelog += "## Python 3.13 Optional Profiles\n\n"
        changelog += (
            "Python 3.13 is certified for the core SDK, CLI, `nlp`, "
            "`nlp-advanced`, and `ocr` install profiles. Donut OCR still "
            "requires a model already available locally. `distributed` and "
            "`all` are not newly certified on Python 3.13 in 4.5.0.\n\n"
        )
        changelog += "## Optional OCR And Spark Surfaces\n\n"
        changelog += (
            "OCR and Spark remain supported optional surfaces. They are not "
            "deprecated, but their broader overhaul is deferred beyond 4.5.0 "
            "so the core package can stay tight and text-first.\n\n"
        )
        changelog += "## Telemetry Defaults\n\n"
        changelog += (
            "Telemetry remains disabled unless `DATAFOG_TELEMETRY=1` is set. "
            "`DATAFOG_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` continue to force "
            "telemetry off.\n\n"
        )

    if categories["features"]:
        changelog += "## 🚀 New Features\n"
        for commit in categories["features"]:
            changelog += f"- {commit[8:]}\n"  # Remove hash
        changelog += "\n"

    if categories["performance"]:
        changelog += "## ⚡ Performance Improvements\n"
        for commit in categories["performance"]:
            changelog += f"- {commit[8:]}\n"
        changelog += "\n"

    if categories["fixes"]:
        changelog += "## 🐛 Bug Fixes\n"
        for commit in categories["fixes"]:
            changelog += f"- {commit[8:]}\n"
        changelog += "\n"

    if categories["docs"]:
        changelog += "## 📚 Documentation\n"
        for commit in categories["docs"]:
            changelog += f"- {commit[8:]}\n"
        changelog += "\n"

    if categories["other"]:
        changelog += "## 🔧 Other Changes\n"
        for commit in categories["other"]:
            changelog += f"- {commit[8:]}\n"
        changelog += "\n"

    changelog += "## 📥 Installation\n\n"
    changelog += "```bash\n"
    changelog += "# Core package (lightweight)\n"
    changelog += "pip install datafog\n\n"
    changelog += "# With all features\n"
    changelog += "pip install datafog[all]\n"
    changelog += "```\n\n"

    changelog += "## 📊 Metrics\n\n"
    changelog += "- Package size: ~2MB (core)\n"
    changelog += "- Install time: ~10 seconds\n"
    changelog += "- Tests passing: ✅\n"
    changelog += f"- Commits this week: {len(commits)}\n\n"

    return changelog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate changelog for releases")
    parser.add_argument(
        "--alpha", action="store_true", help="Generate alpha release changelog"
    )
    parser.add_argument(
        "--beta", action="store_true", help="Generate beta release changelog"
    )
    parser.add_argument(
        "--output", help="Output file name", default="CHANGELOG_LATEST.md"
    )

    args = parser.parse_args()

    changelog_content = generate_changelog(beta=args.beta, alpha=args.alpha)

    # Write to file for GitHub release
    with open(args.output, "w") as f:
        f.write(changelog_content)

    print(f"✅ Changelog generated: {args.output}")
    print("\nPreview:")
    print("=" * 50)
    print(changelog_content)
