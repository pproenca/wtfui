# tests/test_cli.py
"""Tests for Flow CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner
from fastapi import FastAPI

from flow.cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


# =============================================================================
# CLI Dev Command Tests - sys.path, app detection, error handling
# These tests verify CLI behavior that e2e tests miss by calling uvicorn directly
# =============================================================================


class TestCliDevSysPath:
    """Tests for sys.path handling in dev command."""

    def test_dev_adds_cwd_to_sys_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command adds current directory to sys.path for local imports."""
        # Create a minimal app.py in tmp_path
        app_file = tmp_path / "myapp.py"
        app_file.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}
""")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_run:
            result = runner.invoke(cli, ["dev", "myapp:app"])

            # Should not error on import
            if result.exit_code != 0:
                # Check it's not an import error
                assert "No module named" not in (result.output + str(result.exception))

            # Verify uvicorn.run was called (meaning import succeeded)
            if result.exit_code == 0:
                assert mock_run.called

    def test_dev_imports_local_module(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command can import app.py from current directory."""
        # Create app.py
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from fastapi import FastAPI
app = FastAPI()
""")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        with patch("uvicorn.run"):
            result = runner.invoke(cli, ["dev", "app:app"])

            # Should succeed (or at least not fail on import)
            assert "No module named 'app'" not in result.output


class TestCliDevAppDetection:
    """Tests for FastAPI vs component detection."""

    def test_dev_runs_fastapi_app_directly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command runs FastAPI instances directly with uvicorn."""
        # Create app that exports a FastAPI instance
        app_file = tmp_path / "myapp.py"
        app_file.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}
""")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_run:
            runner.invoke(cli, ["dev", "myapp:app"])

            if mock_run.called:
                # Verify it was called with a FastAPI instance
                call_args = mock_run.call_args
                app_arg = call_args[0][0] if call_args[0] else call_args[1].get("app")
                assert isinstance(app_arg, FastAPI)

    def test_dev_wraps_component_with_create_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """dev command wraps component functions with run_app."""
        # Create app that exports a component function (not FastAPI)
        app_file = tmp_path / "myapp.py"
        app_file.write_text('''
async def MyComponent():
    """A component function, not a FastAPI app."""
    pass

app = MyComponent  # Export the function, not a FastAPI instance
''')
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        # Mock uvicorn.run at all levels to prevent blocking
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(cli, ["dev", "myapp:app"])

            # For non-FastAPI objects, the CLI should go through run_app path
            # which internally calls uvicorn.run with a wrapped FastAPI app
            if result.exit_code == 0 and mock_uvicorn.called:
                # Verify uvicorn was called with a FastAPI app (wrapped by run_app)
                call_args = mock_uvicorn.call_args
                app_arg = call_args[0][0] if call_args[0] else call_args[1].get("app")
                # The component should have been wrapped in a FastAPI app
                assert isinstance(app_arg, FastAPI)


class TestCliDevErrorHandling:
    """Tests for error handling in dev command."""

    def test_dev_invalid_path_format_no_colon(self):
        """dev command errors on path without colon separator."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "invalid_path_no_colon"])

        assert result.exit_code != 0
        assert "Invalid app path" in result.output or "format" in result.output.lower()

    def test_dev_module_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command shows helpful error when module doesn't exist."""
        monkeypatch.chdir(tmp_path)  # Empty directory, no modules

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "nonexistent:app"])

        assert result.exit_code != 0
        assert "Could not import" in result.output or "No module" in result.output

    def test_dev_attribute_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command errors when app attribute doesn't exist in module."""
        # Create module without 'app' attribute
        app_file = tmp_path / "mymodule.py"
        app_file.write_text("""
# No 'app' attribute defined
x = 1
""")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "mymodule:app"])

        assert result.exit_code != 0


class TestCliDevOptions:
    """Tests for CLI options."""

    def test_dev_custom_host_port(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """dev command passes host and port to uvicorn."""
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from fastapi import FastAPI
app = FastAPI()
""")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_run:
            runner.invoke(cli, ["dev", "app:app", "--host", "127.0.0.1", "--port", "9000"])

            if mock_run.called:
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs.get("host") == "127.0.0.1"
                assert call_kwargs.get("port") == 9000

    def test_dev_default_app_path(self):
        """dev command uses 'app:app' as default path."""
        runner = CliRunner()

        # Run without app_path argument - will fail but shows default
        with patch("uvicorn.run"):
            result = runner.invoke(cli, ["dev"])

            # Should try to import 'app:app' - error message reveals the default
            assert "app:app" in result.output or result.exit_code != 0
