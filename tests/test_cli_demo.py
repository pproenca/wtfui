"""Tests for the console demo CLI command."""

from __future__ import annotations


def test_demo_module_exists():
    """Demo module can be imported."""
    from flow.cli import demo

    assert demo is not None


def test_demo_has_run_function():
    """Demo module has main entry point."""
    from flow.cli.demo import run_demo

    assert callable(run_demo)


def test_demo_command_registered():
    """Demo command is registered in CLI."""
    from flow.cli import cli

    # Check that 'demo' command exists in the CLI group
    assert "demo" in cli.commands
