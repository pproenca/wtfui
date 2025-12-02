# tests/test_cli.py
"""Tests for Flow CLI commands."""

from click.testing import CliRunner

from flow.cli import cli


def test_cli_exists():
    """CLI entry point exists."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Flow" in result.output


def test_dev_command_exists():
    """flow dev command is available."""
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "--help"])

    assert result.exit_code == 0
    assert "dev" in result.output.lower() or "help" in result.output.lower()


def test_build_command_exists():
    """flow build command is available."""
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--help"])

    assert result.exit_code == 0
    assert "build" in result.output.lower() or "help" in result.output.lower()


def test_new_command_exists():
    """flow new command is available."""
    runner = CliRunner()
    result = runner.invoke(cli, ["new", "--help"])

    assert result.exit_code == 0
