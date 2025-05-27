#!/usr/bin/env python3
"""
Weekly metrics tracking script for DataFog releases.

Collects and stores metrics for weekly release analysis including:
- PyPI download statistics
- GitHub repository metrics
- Package size and performance data
- Test coverage information
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict

import requests


def get_current_version() -> str:
    """Get current version from package."""
    try:
        from datafog import __version__

        return __version__
    except ImportError:
        # Fallback to setup.py
        with open("setup.py", "r") as f:
            for line in f:
                if "version=" in line:
                    return line.split('"')[1]
    return "unknown"


def get_pypi_stats(package_name: str = "datafog") -> Dict[str, Any]:
    """Get PyPI download and package statistics."""
    try:
        # Get package info from PyPI API
        response = requests.get(
            f"https://pypi.org/pypi/{package_name}/json", timeout=10
        )
        response.raise_for_status()
        data = response.json()

        info = data.get("info", {})
        latest_release = data.get("releases", {}).get(info.get("version", ""), [])

        # Calculate package size from wheel if available
        wheel_size = 0
        for file_info in latest_release:
            if file_info.get("packagetype") == "bdist_wheel":
                wheel_size = file_info.get("size", 0) / (1024 * 1024)  # Convert to MB
                break

        return {
            "version": info.get("version", "unknown"),
            "description": info.get("summary", ""),
            "wheel_size_mb": round(wheel_size, 2),
            "upload_time": (
                latest_release[0].get("upload_time") if latest_release else None
            ),
            "python_requires": info.get("requires_python", ""),
        }
    except Exception as e:
        print(f"Error fetching PyPI stats: {e}")
        return {"error": str(e)}


def get_github_stats(repo: str = "datafog/datafog-python") -> Dict[str, Any]:
    """Get GitHub repository statistics."""
    try:
        # Use GitHub API
        headers = {}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

        response = requests.get(
            f"https://api.github.com/repos/{repo}", headers=headers, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "watchers": data.get("subscribers_count", 0),
            "size_kb": data.get("size", 0),
            "default_branch": data.get("default_branch", "main"),
            "last_push": data.get("pushed_at"),
        }
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
        return {"error": str(e)}


def get_local_metrics() -> Dict[str, Any]:
    """Get local package and test metrics."""
    metrics = {}

    try:
        # Get wheel size by building
        subprocess.run(
            ["python", "-m", "build", "--wheel"],
            capture_output=True,
            check=True,
            cwd=".",
        )

        # Find wheel file and get size
        wheel_files = [f for f in os.listdir("dist") if f.endswith(".whl")]
        if wheel_files:
            wheel_path = os.path.join("dist", wheel_files[-1])  # Latest wheel
            size_mb = os.path.getsize(wheel_path) / (1024 * 1024)
            metrics["local_wheel_size_mb"] = round(size_mb, 2)
    except Exception as e:
        print(f"Error building wheel: {e}")
        metrics["local_wheel_size_mb"] = "error"

    try:
        # Get test coverage if coverage file exists
        if os.path.exists("coverage.xml"):
            with open("coverage.xml", "r") as f:
                content = f.read()
                # Simple extraction of coverage percentage
                if 'line-rate="' in content:
                    start = content.find('line-rate="') + len('line-rate="')
                    end = content.find('"', start)
                    coverage = float(content[start:end]) * 100
                    metrics["test_coverage_percent"] = round(coverage, 1)
    except Exception as e:
        print(f"Error reading coverage: {e}")
        metrics["test_coverage_percent"] = "unknown"

    try:
        # Count test files
        test_files = len(
            [
                f
                for f in os.listdir("tests")
                if f.startswith("test_") and f.endswith(".py")
            ]
        )
        metrics["test_file_count"] = test_files
    except Exception:
        metrics["test_file_count"] = "unknown"

    return metrics


def get_git_stats() -> Dict[str, Any]:
    """Get git repository statistics."""
    try:
        # Get commit count for current week
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={week_ago}"],
            capture_output=True,
            text=True,
            check=True,
        )
        commits_this_week = (
            len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        )

        # Get total commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        total_commits = int(result.stdout.strip())

        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()

        return {
            "commits_this_week": commits_this_week,
            "total_commits": total_commits,
            "current_branch": current_branch,
        }
    except Exception as e:
        print(f"Error fetching git stats: {e}")
        return {"error": str(e)}


def generate_weekly_report() -> Dict[str, Any]:
    """Generate comprehensive weekly metrics report."""
    current_time = datetime.now()
    week_number = current_time.strftime("%Y-W%U")

    print("📊 Generating weekly metrics report...")

    metrics = {
        "week": week_number,
        "generated_at": current_time.isoformat(),
        "version": get_current_version(),
    }

    print("  • Fetching PyPI statistics...")
    metrics["pypi"] = get_pypi_stats()

    print("  • Fetching GitHub statistics...")
    metrics["github"] = get_github_stats()

    print("  • Collecting local metrics...")
    metrics["local"] = get_local_metrics()

    print("  • Analyzing git repository...")
    metrics["git"] = get_git_stats()

    # Add some computed metrics
    metrics["computed"] = {
        "is_friday_release": current_time.weekday() == 4,  # Friday = 4
        "days_since_monday": current_time.weekday(),
    }

    return metrics


def save_metrics(metrics: Dict[str, Any]) -> None:
    """Save metrics to file and display summary."""
    # Ensure metrics directory exists
    os.makedirs("metrics", exist_ok=True)

    # Save to JSON file
    filename = f"metrics/week_{metrics['week']}.json"
    with open(filename, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Metrics saved to {filename}")

    # Display summary
    print("\n📈 Weekly Summary:")
    print(f"   Version: {metrics['version']}")

    if "github" in metrics and "stars" in metrics["github"]:
        print(f"   GitHub Stars: {metrics['github']['stars']}")

    if "local" in metrics and "local_wheel_size_mb" in metrics["local"]:
        print(f"   Package Size: {metrics['local']['local_wheel_size_mb']} MB")

    if "local" in metrics and "test_coverage_percent" in metrics["local"]:
        print(f"   Test Coverage: {metrics['local']['test_coverage_percent']}%")

    if "git" in metrics and "commits_this_week" in metrics["git"]:
        print(f"   Commits This Week: {metrics['git']['commits_this_week']}")


def main():
    """Main function to generate and save weekly metrics."""
    try:
        metrics = generate_weekly_report()
        save_metrics(metrics)

        print("\n🎯 Next Steps:")
        print("   1. Review metrics for any anomalies")
        print("   2. Compare with previous weeks")
        print("   3. Update release notes with key numbers")
        print("   4. Prepare social media posts")

    except Exception as e:
        print(f"❌ Error generating metrics: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
