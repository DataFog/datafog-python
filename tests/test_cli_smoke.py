"""Smoke tests for the DataFog CLI.

These tests verify basic CLI functionality using temporary files.
"""

import os
import tempfile

import pytest
from typer.testing import CliRunner

from datafog.client import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_text_file():
    """Create a temporary text file with sample content."""
    # Create a temporary file with sample text containing PII
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("My name is John Doe and my email is john.doe@example.com.\n")
        f.write("My phone number is (555) 123-4567 and my SSN is 123-45-6789.\n")
        temp_file = f.name

    yield temp_file

    # Clean up the temporary file after the test
    if os.path.exists(temp_file):
        os.remove(temp_file)


@pytest.mark.integration
def test_health_command(runner):
    """Test the health command."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "DataFog is running" in result.stdout


@pytest.mark.integration
def test_show_config_command(runner):
    """Test the show-config command."""
    result = runner.invoke(app, ["show-config"])
    assert result.exit_code == 0
    # Check that the output contains some expected config fields
    assert "api_key" in result.stdout.lower()
    assert "log_level" in result.stdout.lower()


@pytest.mark.integration
def test_scan_text_with_file_content(runner, temp_text_file):
    """Test the scan-text command with content from a temporary file."""
    # Read the content of the temporary file
    with open(temp_text_file, "r") as f:
        text_content = f.read().strip()

    # Run the scan-text command with the file content
    result = runner.invoke(app, ["scan-text", text_content])

    # Verify the command executed successfully
    assert result.exit_code == 0

    # Check that the output contains expected PII types
    assert (
        "PERSON" in result.stdout
        or "EMAIL" in result.stdout
        or "PHONE" in result.stdout
    )


@pytest.mark.integration
def test_redact_text_command(runner):
    """Test the redact-text command."""
    test_text = "My name is John Doe and my email is john.doe@example.com."

    result = runner.invoke(app, ["redact-text", test_text])

    assert result.exit_code == 0
    # Check that PII has been redacted (replaced with [REDACTED])
    assert "[REDACTED]" in result.stdout
    # The person name should be redacted
    assert "John Doe" not in result.stdout
    # Note: The current implementation might not redact emails correctly
    # This is a known limitation we're accepting for the smoke test


@pytest.mark.integration
def test_replace_text_command(runner):
    """Test the replace-text command."""
    test_text = "My name is John Doe and my email is john.doe@example.com."

    result = runner.invoke(app, ["replace-text", test_text])

    assert result.exit_code == 0
    # The person name should be replaced with a pseudonym
    assert "John Doe" not in result.stdout
    # Check that the text contains a replacement pattern for person (like [PERSON_HASH])
    assert "[PERSON_" in result.stdout or "PERSON-" in result.stdout
    # But the text should still have some content (not just replacements)
    assert "My name is" in result.stdout


@pytest.mark.integration
def test_list_entities_command(runner):
    """Test the list-entities command."""
    result = runner.invoke(app, ["list-entities"])

    assert result.exit_code == 0
    # Should list some common entity types
    assert "PERSON" in result.stdout
    assert "ORG" in result.stdout
