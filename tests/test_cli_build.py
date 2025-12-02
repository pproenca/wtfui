"""Tests for CLI build command."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from flow.cli import cli


def test_build_creates_output_directory():
    """build command creates output directory."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal app file
        app_file = Path(tmpdir) / "myapp.py"
        app_file.write_text("""
from flow import component
from flow.ui import Div

@component
async def App():
    with Div():
        pass

app = App
""")

        output_dir = Path(tmpdir) / "dist"

        with patch("sys.path", [tmpdir, *__import__("sys").path]):
            result = runner.invoke(cli, ["build", "myapp:app", "-o", str(output_dir)])

        assert result.exit_code == 0, result.output
        assert output_dir.exists()


def test_build_creates_index_html():
    """build command creates index.html."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = Path(tmpdir) / "myapp.py"
        app_file.write_text("""
from flow import component
from flow.ui import Div

@component
async def App():
    with Div():
        pass

app = App
""")

        output_dir = Path(tmpdir) / "dist"

        with patch("sys.path", [tmpdir, *__import__("sys").path]):
            result = runner.invoke(cli, ["build", "myapp:app", "-o", str(output_dir)])

        assert result.exit_code == 0
        index_file = output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()
        assert "pyodide" in content.lower()


def test_build_creates_client_bundle():
    """build command creates client Python bundle."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = Path(tmpdir) / "myapp.py"
        app_file.write_text("""
import sqlalchemy  # Server-only
from flow import component
from flow.ui import Div

@component
async def App():
    with Div():
        pass

app = App
""")

        output_dir = Path(tmpdir) / "dist"

        with patch("sys.path", [tmpdir, *__import__("sys").path]):
            result = runner.invoke(cli, ["build", "myapp:app", "-o", str(output_dir)])

        assert result.exit_code == 0
        client_file = output_dir / "client" / "myapp.py"
        assert client_file.exists()
        content = client_file.read_text()
        # Server import should be stripped
        assert "import sqlalchemy" not in content


def test_build_shows_completion_message():
    """build command shows completion message."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = Path(tmpdir) / "myapp.py"
        app_file.write_text("""
from flow import component
from flow.ui import Div

@component
async def App():
    pass

app = App
""")

        output_dir = Path(tmpdir) / "dist"

        with patch("sys.path", [tmpdir, *__import__("sys").path]):
            result = runner.invoke(cli, ["build", "myapp:app", "-o", str(output_dir)])

        assert "Build complete" in result.output or "complete" in result.output.lower()
