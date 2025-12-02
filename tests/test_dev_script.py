# tests/test_dev_script.py
"""Tests for the dev script."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def dev_script() -> Path:
    """Path to the dev script."""
    script = Path(__file__).parent.parent / "dev"
    assert script.exists(), "dev script not found"
    return script


def test_dev_script_is_executable(dev_script: Path):
    """Dev script should be executable."""
    import os

    assert os.access(dev_script, os.X_OK)


def test_dev_script_help(dev_script: Path):
    """Dev script help command works."""
    result = subprocess.run(
        [str(dev_script), "help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "setup" in result.stdout
    assert "start" in result.stdout
    assert "test" in result.stdout


def test_dev_script_unknown_command(dev_script: Path):
    """Dev script handles unknown commands."""
    result = subprocess.run(
        [str(dev_script), "unknown_command"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Unknown command" in result.stdout or "Unknown command" in result.stderr
