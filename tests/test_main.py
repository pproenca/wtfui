"""Tests for WtfUI Meta-CLI (main.py)."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestMetaCLIHelp:
    """Tests for help output."""

    def test_help_shows_all_commands(self):
        """Help output includes all commands."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "init" in result.stdout
        assert "install" in result.stdout
        assert "dev" in result.stdout
        assert "build" in result.stdout
        assert "clean" in result.stdout

    def test_version_shows_version(self):
        """--version shows version string."""
        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "--version"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Flow" in result.stdout or "0.1.0" in result.stdout


class TestMetaCLIInit:
    """Tests for init command."""

    def test_init_creates_wtfui_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init creates wtfui.toml in new project."""
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "myapp"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / "myapp" / "wtfui.toml").exists()

    def test_init_creates_pyproject(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init creates pyproject.toml for dependencies."""
        monkeypatch.chdir(tmp_path)

        subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "myapp"],
            capture_output=True,
            text=True,
        )

        assert (tmp_path / "myapp" / "pyproject.toml").exists()

    def test_init_creates_app_py(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init creates app.py with starter code."""
        monkeypatch.chdir(tmp_path)

        subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "myapp"],
            capture_output=True,
            text=True,
        )

        app_py = tmp_path / "myapp" / "app.py"
        assert app_py.exists()
        content = app_py.read_text()
        assert "Signal" in content
        assert "app = " in content or "app=" in content

    def test_init_fails_if_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init fails if directory already exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing").mkdir()

        result = subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "init", "existing"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "exists" in result.stderr.lower()


class TestMetaCLIClean:
    """Tests for clean command."""

    def test_clean_removes_pycache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """clean removes __pycache__ directories."""
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "test.pyc").touch()

        subprocess.run(
            [sys.executable, "-m", "wtfui.cli.main", "clean"],
            capture_output=True,
            text=True,
        )

        assert not cache_dir.exists()


class TestMetaCLIProjectDiscovery:
    """Tests for project-based command routing."""

    def test_dev_with_project_name_finds_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """wtfui dev myproject finds project by name."""
        monkeypatch.chdir(tmp_path)

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
