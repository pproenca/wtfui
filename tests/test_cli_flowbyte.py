"""Tests for FlowByte CLI build command."""

import pytest
from click.testing import CliRunner

from flow.cli import cli
from flow.compiler.writer import MAGIC_HEADER


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_app(tmp_path, monkeypatch):
    """Create a sample Flow app for building."""
    app_file = tmp_path / "app.py"
    app_file.write_text("""
from flow import component
from flow.ui import Div, Text, Button
from flow.signal import Signal

count = Signal(0)

@component
async def App():
    with Div() as root:
        Text(f"Count: {count.value}")
    return root

app = App
""")
    # Change to the temp directory so the CLI can find app.py
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestFlowByteBuild:
    """Test flow build --format=flowbyte."""

    def test_build_creates_fbc_file(self, runner, sample_app) -> None:
        """flow build creates .fbc binary file."""
        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "flowbyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (sample_app / "dist" / "app.fbc").exists()

    def test_fbc_file_has_magic_header(self, runner, sample_app) -> None:
        """Generated .fbc file starts with FLOW header."""
        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "flowbyte"],
        )

        fbc_content = (sample_app / "dist" / "app.fbc").read_bytes()
        assert fbc_content.startswith(MAGIC_HEADER)

    def test_build_generates_vm_shell(self, runner, sample_app) -> None:
        """flow build creates HTML shell that loads VM."""
        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "flowbyte"],
        )

        html = (sample_app / "dist" / "index.html").read_text()
        assert "FlowVM" in html
        assert "app.fbc" in html
