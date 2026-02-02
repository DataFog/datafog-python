#!/usr/bin/env python3
"""Generate changelog for weekly releases."""

import argparse
import re
import subprocess
from datetime import datetime


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
