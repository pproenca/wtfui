"""Tests for WtfUIByte CLI build command."""

import json

import pytest
from click.testing import CliRunner

from wtfui.cli import cli
from wtfui.web.compiler.writer import MAGIC_HEADER


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_app(tmp_path, monkeypatch):
    """Create a sample WtfUI app for building."""
    app_file = tmp_path / "app.py"
    app_file.write_text("""
from wtfui import component
from wtfui.ui import Div, Text, Button
from wtfui.core.signal import Signal

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


class TestWtfUIByteBuild:
    """Test wtfui build --format=wtfuibyte."""

    def test_build_creates_fbc_file(self, runner, sample_app) -> None:
        """wtfui build creates .mfbc binary file."""
        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (sample_app / "dist" / "app.mfbc").exists()

    def test_fbc_file_has_magic_header(self, runner, sample_app) -> None:
        """Generated .mfbc file starts with MYFU header."""
        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
        )

        fbc_content = (sample_app / "dist" / "app.mfbc").read_bytes()
        assert fbc_content.startswith(MAGIC_HEADER)

    def test_build_generates_vm_shell(self, runner, sample_app) -> None:
        """wtfui build creates HTML shell that loads VM."""
        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
        )

        html = (sample_app / "dist" / "index.html").read_text()
        assert "WtfUIVM" in html
        assert "app.mfbc" in html

    def test_build_wtfuibyte_generates_css_file(self, runner, sample_app) -> None:
        """wtfui build generates app.css alongside app.mfbc."""
        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Both files should exist
        assert (sample_app / "dist" / "app.mfbc").exists()
        assert (sample_app / "dist" / "app.css").exists()

    def test_css_file_contains_atomic_classes(self, runner, tmp_path, monkeypatch) -> None:
        """Generated CSS contains atomic classes when styles are present."""
        # Create app with styled components
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from wtfui import component
from wtfui.ui import Div, Text

@component
async def App():
    with Div(style={"background": "blue", "padding": "4px"}) as root:
        Text("Styled content")
    return root

app = App
""")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        css_content = (tmp_path / "dist" / "app.css").read_text()
        # CSS should contain atomic class prefix
        assert ".fl-" in css_content

    def test_html_links_to_css_file(self, runner, sample_app) -> None:
        """Generated HTML includes link to app.css."""
        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
        )

        html = (sample_app / "dist" / "index.html").read_text()
        assert '<link rel="stylesheet" href="app.css">' in html

    def test_build_generates_styles_manifest(self, runner, tmp_path, monkeypatch) -> None:
        """wtfui build generates styles.json manifest when styles are present."""
        # Create app with styled components
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from wtfui import component
from wtfui.ui import Div, Text

@component
async def App():
    with Div(style={"background": "blue", "padding": "4px"}) as root:
        Text("Styled content")
    return root

app = App
""")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Manifest file should exist
        manifest_file = tmp_path / "dist" / "styles.json"
        assert manifest_file.exists()

        # Manifest should be valid JSON with style classes
        manifest = json.loads(manifest_file.read_text())
        assert isinstance(manifest, dict)
        # Should have at least one class (for the background and padding styles)
        assert len(manifest) > 0

        # Classes should have fl- prefix
        assert any(k.startswith("fl-") for k in manifest)

        # Each entry should be a dict of CSS properties
        for _class_name, properties in manifest.items():
            assert isinstance(properties, dict)
            assert all(isinstance(k, str) and isinstance(v, str) for k, v in properties.items())

    def test_manifest_contains_style_properties(self, runner, tmp_path, monkeypatch) -> None:
        """Manifest contains the actual CSS properties from registered styles."""
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from wtfui import component
from wtfui.ui import Div, Text

@component
async def App():
    with Div(style={"background": "blue", "padding": "4px"}) as root:
        Text("Test")
    return root

app = App
""")
        monkeypatch.chdir(tmp_path)

        runner.invoke(
            cli,
            ["build", "app:app", "--output", "dist", "--format", "wtfuibyte"],
            catch_exceptions=False,
        )

        manifest_file = tmp_path / "dist" / "styles.json"
        manifest = json.loads(manifest_file.read_text())

        # Check that the manifest contains expected CSS properties
        # The CSSGenerator should normalize "background" to "background-color"
        # and add "px" to padding
        found_bg = False
        found_padding = False
        for properties in manifest.values():
            if "background-color" in properties or "background" in properties:
                found_bg = True
            if "padding" in properties:
                found_padding = True

        assert found_bg or found_padding
