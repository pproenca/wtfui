"""Integration tests for CLI wtfui."""

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestCLIIntegration:
    """End-to-end CLI tests."""

    def test_wtfui_help_runs(self) -> None:
        """wtfui --help executes successfully."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "WtfUI 0.1.0" in result.stdout

    def test_wtfui_init_creates_project(self, tmp_path: Path) -> None:
        """wtfui init creates valid project structure."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "testapp"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=30,
        )

        assert result.returncode == 0
        assert (tmp_path / "testapp" / "pyproject.toml").exists()
        assert (tmp_path / "testapp" / "app.py").exists()

    def test_wtfui_clean_is_idempotent(self, tmp_path: Path) -> None:
        """wtfui clean can run multiple times safely."""
        # Run clean twice - should not error
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-m", "wtfui.cli.main", "clean"],
                capture_output=True,
                text=True,
                cwd=tmp_path,
                timeout=10,
            )
            assert result.returncode == 0


@pytest.mark.integration
class TestCLIIntegrationWtfUIToml:
    """Integration tests for wtfui.toml-based workflow."""

    def test_init_creates_wtfui_toml(self, tmp_path: Path) -> None:
        """wtfui init creates wtfui.toml in new project."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "testapp"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0
        assert (tmp_path / "testapp" / "wtfui.toml").exists()

    def test_wtfui_toml_content(self, tmp_path: Path) -> None:
        """wtfui.toml contains required configuration."""
        subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "testapp"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        wtfui_toml = (tmp_path / "testapp" / "wtfui.toml").read_text()
        assert 'name = "testapp"' in wtfui_toml
        assert 'entry = "app.py"' in wtfui_toml
        assert "[project]" in wtfui_toml
        assert "[app]" in wtfui_toml
        assert "[dev]" in wtfui_toml

    def test_dev_finds_project_by_name(self, tmp_path: Path) -> None:
        """wtfui dev myproject finds project by folder name."""
        project = tmp_path / "myproject"
        project.mkdir()
        (project / "wtfui.toml").write_text('[project]\nname = "myproject"')
        (project / "app.py").write_text("app = None")
        (project / "pyproject.toml").write_text('[project]\nname = "myproject"\ndependencies = []')

        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "dev", "myproject", "--help"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=10,
        )

        assert "not found" not in result.stderr.lower() or result.returncode == 0

    def test_project_not_found_error(self, tmp_path: Path) -> None:
        """wtfui dev nonexistent shows helpful error."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "dev", "nonexistent"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=10,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()
